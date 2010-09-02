from django.http import HttpResponse
from django.template.loader import get_template
from django.template import Context
from gallery.models import Annotation, AnnotationOwner, AnnotationObject, Experiment, ExperimentInfo, AnnotationFeature
import random, math, time

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
    target_img = random.choice(objs)
    
    request.session.flush()
    
    e = Experiment(
            sessionid=request.session.session_key,
            iterations=0,
            finished=False,
            target=target_img,
            number_of_images=2,
            alpha=100,
            count=100
            )
    e.save()
    
#    # 3. initialise variables in dirchlet distribution
#    request.session['basemeasures'] = [ 1 / float(len(objs)) ] * len(objs)
    
    html = t.render(Context({'image' : '/site_media/' + target_img.filename}))
    return HttpResponse(html)

def bad_session(request) :
    t = get_template('bad_session.html')
    html = t.render(Context({ 
                        'sessionid' : request.session.session_key 
                    }))
    return HttpResponse(html)

def good_enough(request, state) :
    try :
        e = Experiment.objects.get(sessionid=request.session.session_key)
    except :
        return bad_session(request)
    
    e.finished = True
    e.save()

    ei = ExperimentInfo.objects.get(experiment=e, iteration=e.iterations-1)
    ei.selection = state
    ei.save()

    t = get_template('finished.html')
    html = t.render(Context({
                        'target': '/site_media/' + e.target.filename, 
                        'image' : '/site_media/' + state, 
                        'iterations': e.iterations
                    }))
    
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
    start_search = time.time()
    objs = Annotation.objects.all()
    
    try :
        e = Experiment.objects.get(sessionid=request.session.session_key)
    except :
        return bad_session(request)
    
#    basemeasures = request.session['basemeasures']
    basemeasures = None

    # this is the first time that do_search has been called
    # for the current session id
    if state == 'start' :
        e.number_of_images = int(request.GET['num'])
        e.algorithm = request.GET.get('algorithm', 'dirchlet')
        request.session['debug'] = bool(int(request.GET.get('debug', 0)))
 
        print "algorithm = %s" % e.algorithm

        if e.algorithm == 'dirchlet' :
            # 3. initialise variables in dirchlet distribution
            request.session['basemeasures'] = [ 1 / float(len(objs)) ] * len(objs)
        elif e.algorithm == 'auer' :
            request.session['basemeasures'] = [ 1.0 ] * len(objs)
        else :
            pass

    # none of the images were suitable, so ignore the last
    # round
    elif state == 'ignore' :
        pass
    # everything else, random, auer or dirchlet...
    else :
        ei = ExperimentInfo.objects.get(experiment=e, iteration=e.iterations-1)
        ei.selection = state
        ei.save()

        print "DEBUG: %f" % calc_distance2(e.target, Annotation.objects.get(filename=state))
        
        if e.algorithm != 'random' :
            basemeasures = request.session['basemeasures']

            # 5. calculate distance from all images show to all images in database
            feature_cache = {}
            start_time = time.time()
            for i in objs :
                feature_cache[i] = featuredict(i)
            print "\tcaching features: %d seconds" % (int(time.time() - start_time))
            
            distances = {}
            start_time = time.time()
            for i in objs :
                distances[i] = map(lambda x : calc_distance(feature_cache[i], feature_cache[x]) , ei.options.all())
            print "\tdistance calculations: %d seconds" % (int(time.time() - start_time))
            
            
            # 6. find minimum of each images in dataset to shown images
            index = map(lambda x : x.filename, ei.options.all()).index(ei.selection)
            count = 0
            for i in distances :
                m = min(distances[i])
                # 7a. update base measures of closest images to user selected by 1
                #     update count by 1
                if distances[i][index] == m :
                    if e.algorithm == 'dirchlet' :
                        basemeasures[count] += 1
                        e.count += 1
                else :
                    if e.algorithm == 'auer' :
                        basemeasures[count] *= 0.6
                    pass

                count += 1
            
            # 7b. renormalise basemeasures
            #basemeasures = map(lambda x : x / e.count, basemeasures)
            request.session['basemeasures'] = basemeasures   
    
    ######################################################
    #  select images to be displayed for the next round  #
    ######################################################
    k = e.number_of_images
    alg = e.algorithm

    if alg == 'random' :
        samp = random.sample(objs, k)
    
    elif alg == 'dirchlet' :
        basemeasures = request.session['basemeasures']
        # 4a. update dirchlet distribution base measures 
        #basemeasures = map(lambda x : x * e.count, basemeasures) # this just undoes line 173 (dorota knows)
        #request.session['basemeasures'] = basemeasures

        # 4b. select k images to show user
        samp = []
        for i in range(k) :
            z = map(
                    lambda x : (random.gammavariate(basemeasures[x], 1), x), 
                    range(len(basemeasures))
                )
            z.sort(reverse=True)
            for gvar,index in z :
                if objs[index] not in samp : # don't want any repeats in sample (just in case...)
                    samp.append(objs[index])
                    break

    elif alg == 'auer' :
        basemeasures = request.session['basemeasures']
        samp = []
        total = float(sum(basemeasures))
        for i in range(k) :
            r = random.random()
            z = 0
            index = 0
            while True :
                z += (basemeasures[index] / total)
                index += 1
                if z >= r :
                    if objs[index] not in samp :
                        samp.append(objs[index])
                        break
                    z = 0
                    index = 0

    else :
        pass
    
    #######################
    #  record info in db  #
    #######################
    ei = ExperimentInfo(
                experiment=e,
                iteration=e.iterations,
                selection='none'
            )
    ei.save()
    for s in samp :
        ei.options.add(s)
    
    e.iterations += 1
    e.save()
    
    #########################
    #  display to the user  #
    #########################
    images = []
    for s in samp :
        images.append({ 'image': "/site_media/%s" % s.filename,
                        'link': "/search/%s/" % (s.filename),
                        'finish' : "/finish/%s/" % s.filename,
                        'distance' : str(calc_distance2(s, e.target))
                        })

    print "DEBUG: " + ' '.join(map(lambda x : "%f" % float(x['distance']), images))

    t = get_template('gallery.html')
    html = t.render(Context({
                        'image_list' : images, 
                        'debug' : request.session['debug'], 
                        'random' : int(alg == 'random')
                    }))
    
    print "\tdo_search(): %d seconds" % (int(time.time() - start_search))
    return HttpResponse(html)

