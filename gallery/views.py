from django.http import HttpResponse
from django.template.loader import get_template
from django.template import Context
from gallery.models import Annotation, AnnotationOwner, AnnotationObject, Experiment, ExperimentInfo, ExperimentBaseMeasure, AnnotationFeature
import random, math

def random_pic(request, feature) :
    all = AnnotationObject.objects.filter(name=feature)
    if len(all) == 0 :
        return HttpResponse("<html><body><h2>%s does not exist</h2></body></html>" % feature)

    s = "<html>\
            <body>\
                <h2>" + feature + "<h2><br />\
                <img src=\"/site_media/" \
                    + all[random.randint(0,len(all)-1)].parent_annotation.filename + "\" />\
            </body>\
        </html>"
    return HttpResponse(s)

def random_gallery(request, feature, number) :
    t = get_template('gallery.html')
    objs = AnnotationObject.objects.filter(name=feature)
    image_list = map(lambda x : "/site_media/" + x.parent_annotation.filename, random.sample(objs, int(number)))
    
    html = t.render(Context({'image_list' : image_list, \
                             'link' : "/gallery/%s/%s/" % (feature, number), \
                             'alttext' : feature }))
    
    return HttpResponse(html)

def start_search(request):
    t = get_template('start.html')
    objs = Annotation.objects.all()
    
    # 2. select an image to show to the user
    target = random.choice(objs)
    
    request.session.flush()
    
    e = Experiment()
    e.sessionid = request.session.session_key
    e.iterations = 0
    e.finished = False
    e.target = target
    e.number_of_images = 2
    e.alpha = 100
    e.count = e.alpha
    e.save()

    # 3. initialise variables in dirchlet distribution (ExperimentBaseMeasure objects)
    val = 1 / float(len(objs))
#    for o in objs :
#        i = ExperimentBaseMeasure()
#        i.experiment = e
#        i.name = o
#        i.value = val
#        i.save()
    x = []
    for i in range(len(objs)):
        x.append(val)
    request.session['basemeasures'] = x
    
    
    html = t.render(Context({'image' : '/site_media/' + target.filename}))
    
    return HttpResponse(html)

def featuredict(annotation) :
    d = {}
    for f in AnnotationFeature.objects.filter(parent=annotation) :
        d[f.name] = f.value

    return d

def calc_distance2(annotation1, annotation2) :
    features1 = featuredict(annotation1)
    features2 = featuredict(annotation2)
    
    total = 0.0
    for k in set(features1.keys() + features2.keys()) :
        f1 = features1.get(k, 0.0)
        f2 = features2.get(k, 0.0)
    
        total += ((f1 - f2) ** 2)
    
    return total

def calc_distance(features1, features2) :
    total = 0.0
    for k in set(features1.keys() + features2.keys()) :
        f1 = features1.get(k, 0.0)
        f2 = features2.get(k, 0.0)
    
        total += ((f1 - f2) ** 2)
    
    return total

def do_search(request, state):
    objs = Annotation.objects.all()
    
    try :
        e = Experiment.objects.get(sessionid=request.session.session_key)
    except :
        t = get_template('bad_session.html')
        html = t.render(Context({ 'sessionid' : request.session.session_key }))
        return HttpResponse(html)
    
    #basemeasures = ExperimentBaseMeasure.objects.filter(experiment=e)
    basemeasures = request.session['basemeasures']

    if state == 'start' :
        e.number_of_images = int(request.GET['num'])
        request.session['debug'] = request.GET.get('debug', 0)
    elif state == 'ignore' :
        pass
    else :
        ei = ExperimentInfo.objects.get(experiment=e, iteration=e.iterations-1)
        ei.selection = state
        ei.save()

        index = 0
        for i in ei.options.all() :
            if i.filename == ei.selection :
                break
            index += 1

        print "[i] %d %s" % (index, i.filename)
        
        # 5. calculate distance from all images show to all images in database
        print "start caching features"
        features = {}
        for i in ei.options.all() :
            features[i] = featuredict(i)
        allfeatures = {}
        for i in objs :
            allfeatures[i] = featuredict(i)
        print "finish caching features"
        
        distances = {}
        print "start distance calculations"
        for i in objs :
            #print i.filename
            distances[i] = map(lambda x : calc_distance(allfeatures[i], features[x]) , ei.options.all())
        print "finish distance calculations"

        # 6. find minimum of each images in dataset to shown images
        count = 0
        for i in distances :
            m = min(distances[i])
            # 7a. update base measures of closest images to user selected by 1
            #     update count by 1
            if distances[i][index] == m :
                #b = basemeasures.get(name=i)
                #b.value += 1
                #b.save()
                basemeasures[count] += 1
                e.count += 1
            count += 1

        # 7b. renormalise basemeasures
        #for bm in basemeasures :
        #    bm.value /= e.count
        for i in range(len(basemeasures)) :
            basemeasures[i] /= e.count

    k = e.number_of_images
    t = get_template('gallery.html')
    
    # 4a. update dirchlet distribution base measures 
    #basemeasures = ExperimentBaseMeasure.objects.filter(experiment=e)
    #for bm in basemeasures :
    #    bm.value *= e.count
    #    bm.save()
    for i in range(len(basemeasures)) :
        basemeasures[i] *= e.count
    request.session['basemeasures'] = basemeasures

    # 4b. select k images to show user
    samp = []
    for i in range(k) :
        #z = map(lambda x : random.gammavariate(x.value, 1), basemeasures)
        z = map(lambda x : random.gammavariate(x, 1), basemeasures)
        zprime = map(lambda x : (z[x], x), range(len(z)))
        zprime.sort(reverse=True)
        for gv,index in zprime :
            if objs[index] not in samp :
                samp.append(objs[index])
                break
    
    # old
    #samp = random.sample(objs, k)

    ei = ExperimentInfo()
    ei.experiment = e
    ei.iteration = e.iterations
    ei.selection = 'none'
    ei.save()
    for s in samp :
        ei.options.add(s)
    #ei.save()

    e.iterations += 1
    e.save()

    images = []
    for s in samp :
        images.append({ 'image': "/site_media/%s" % s.filename,
                        'link': "/search/%s/" % (s.filename),
                        'finish' : "/finish/%s/" % s.filename,
                        'distance' : str(calc_distance2(s, e.target))
                        })
    
    html = t.render(Context({'image_list' : images, 'debug' : request.session['debug']}))
    
    return HttpResponse(html)

def good_enough(request, state) :
    try :
        e = Experiment.objects.get(sessionid=request.session.session_key)
    except :
        t = get_template('bad_session.html')
        html = t.render(Context({ 'sessionid' : request.session.session_key }))
        return HttpResponse(html)
 
    e.finished = True

    ei = ExperimentInfo.objects.get(experiment=e, iteration=e.iterations-1)
    ei.selection = state
    ei.save()

    e.save()

    t = get_template('finished.html')
    html = t.render(Context({'target': '/site_media/' + e.target.filename, 'image' : '/site_media/' + state, 'iterations': e.iterations}))
    
    return HttpResponse(html)

