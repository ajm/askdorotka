from django.http import HttpResponse
from django.template.loader import get_template
from django.template import Context
from gallery.models import Annotation, AnnotationOwner, AnnotationObject, Experiment, ExperimentInfo, AnnotationFeature
import random, math, time


INITIAL_NUM_IMG = 300
INCREMENT_NUM_IMG = 50

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

def add_more_images(basemeasures, objs, usedimages) :
    #unused = Annotation.objects.filter(used=False)
    allimages = Annotation.objects.all()
    unused = filter(lambda x : x.filename not in usedimages, allimages)

    print "add_more_images: starting with %d base measures" % INITIAL_NUM_IMG #len(basemeasures)

#    if len(unused) == 0 :
#        return basemeasures,objs

    try :
        samp = random.sample(unused, INCREMENT_NUM_IMG) #len(basemeasures))
    except ValueError :
        samp = unused
    
    usedimages += map(lambda x : x.filename, samp)

    # calc distances
    distance = {}
    for i in objs :
        f = featuredict(i)
        distance[i] = map(lambda x : calc_distance(f, featuredict(x)), samp)
    
    # put old base measures in dict
    old_basemeasures = {}
    for i in range(len(objs)) :
        old_basemeasures[objs[i]] = basemeasures[i]

    # put new base measures in dict
    new_basemeasures = {}
    for i in objs :
        m = min(distance[i])
        for j in range(len(samp)) :
            if distance[i][j] == m :
                if samp[j] not in new_basemeasures :
                    new_basemeasures[samp[j]] = []

                new_basemeasures[samp[j]].append(old_basemeasures[i])
    
    cutoff = sorted(basemeasures)[INCREMENT_NUM_IMG]
    images_removed = 0

    # change status on new images to used
#    for i in samp :
#        i.used = True
#        i.save()

    # create new basemeasures list
    bm = []
    #newobjs = Annotation.objects.filter(used=True)
    newobjs = filter(lambda x : x.filename in usedimages, allimages)
    returnobjs = []
    for i in newobjs :
        if i in old_basemeasures :
            if (old_basemeasures[i] > cutoff) or (images_removed == INCREMENT_NUM_IMG) :
                bm.append(old_basemeasures[i])
                returnobjs.append(i)
            else :
                images_removed += 1

            continue
        if i in new_basemeasures :
            bm.append(sum(new_basemeasures[i]) / float(len(new_basemeasures[i])))
            returnobjs.append(i)
            continue

        # if no images closest, use 1/n
        bm.append(1 / float(len(newobjs)))
        returnobjs.append(i)

    returnused = map(lambda x : x.filename, returnobjs)

    print "add_more_images: ending with %d base measures" % len(bm)
    
    return bm,returnobjs,returnused


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

        if e.algorithm == 'dirchlet' or e.algorithm == 'dirchlet-zero' or e.algorithm == 'pichunter':
            # 3. initialise variables in dirchlet distribution
            request.session['basemeasures'] = [ 1 / float(len(objs)) ] * len(objs)
        elif e.algorithm == 'auer' or e.algorithm == 'auer-zero' or e.algorithm == 'random' :
            request.session['basemeasures'] = [ 1.0 ] * len(objs)
        elif e.algorithm == 'dirchlet-incremental' or e.algorithm == 'pichunter-incremental':
            request.session['basemeasures'] = [ 1 / float(INITIAL_NUM_IMG) ] * INITIAL_NUM_IMG
        elif e.algorithm == 'auer-incremental' :
            request.session['basemeasures'] = [ 1.0 ] * INITIAL_NUM_IMG
            # select 100 random images & set their 'used' attribute to True
#            for i in objs : # make sure the others are not being used
#                i.used = False
#                i.save()
#            objs = random.sample(objs, 100)
#            for i in objs :
#                i.used = True
#                i.save()

        else :
            pass

            # well that was dog slow...
        if e.algorithm.endswith('incremental') :
            objs = random.sample(objs, INITIAL_NUM_IMG)
            request.session['used-images'] = map(lambda x : x.filename, objs)

    # none of the images were suitable, so ignore the last
    # round
    elif state == 'ignore' :
        if e.algorithm.endswith('incremental') :
            usedimages = request.session['used-images']
            objs = filter(lambda x : x.filename in usedimages, Annotation.objects.all())
            print "DEBUG: using %d images" % len(objs)

    # everything else, random, auer or dirchlet...
    else :
        ei = ExperimentInfo.objects.get(experiment=e, iteration=e.iterations-1)
        ei.selection = state
        ei.save()

        print "DEBUG: %f" % calc_distance2(e.target, Annotation.objects.get(filename=state))
        
        if e.algorithm != 'random' :
            basemeasures = request.session['basemeasures']

            if e.algorithm.endswith('incremental') :
                #objs = Annotation.objects.filter(used=True)
                usedimages = request.session['used-images']
                objs = filter(lambda x : x.filename in usedimages, Annotation.objects.all())
                print "DEBUG: using %d images" % len(objs)
            
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
            
            if not e.algorithm.startswith('pichunter') :
                # 6. find minimum of each images in dataset to shown images
                index = map(lambda x : x.filename, ei.options.all()).index(ei.selection)
                count = 0
                for i in distances :
                    m = min(distances[i])
                    # 7a. update base measures of closest images to user selected by 1
                    #     update count by 1
                    if distances[i][index] == m :
                        #if e.algorithm == 'dirchlet' :
                        if e.algorithm.startswith('dirchlet') :
                            basemeasures[count] += 1
                            e.count += 1
                    else :
                        if e.algorithm.startswith('auer') :
                            basemeasures[count] *= 0.6
                        pass

                    count += 1

                if e.algorithm.endswith('zero') :
                    files = map(lambda x : x.filename, Annotation.objects.all())
                    for i in map(lambda x: files.index(x.filename), ei.options.all()) :
                        basemeasures[i] = 0.000001

                # TODO for dirchlet-incremental double the number of images being
                # used and calculate their weights 

                # 7b. renormalise basemeasures
                #basemeasures = map(lambda x : x / e.count, basemeasures)
#                if e.algorithm.endswith('incremental') :
#                    request.session['basemeasures'],objs,request.session['used-images'] = \
#                        add_more_images(basemeasures, objs, usedimages)
#                else :
#                    request.session['basemeasures'] = basemeasures
                    
            else :
                index = map(lambda x : x.filename, ei.options.all()).index(ei.selection) # find index of selection
                count = 0
                for i in distances :
                    tmp = math.exp(-math.sqrt((distances[i][index])**2)) / 0.1
                    basemeasures[count] *= tmp
                    count += 1
                
                if e.algorithm.endswith('incremental') :
                    usedimages = request.session['used-images']
                    files = map(lambda y : y.filename, filter(lambda x : x.filename in usedimages, Annotation.objects.all()))
                else :
                    files = map(lambda x : x.filename, Annotation.objects.all())
                
                for i in map(lambda x: files.index(x.filename), ei.options.all()) :
                    basemeasures[i] = 0.0
                
                total = float(sum(basemeasures))
                request.session['basemeasures'] = map(lambda x : x / total, basemeasures)
                
            if e.algorithm.endswith('incremental') :
                request.session['basemeasures'],objs,request.session['used-images'] = \
                    add_more_images(basemeasures, objs, usedimages)
            else :
                request.session['basemeasures'] = basemeasures
    
    ######################################################
    #  select images to be displayed for the next round  #
    ######################################################
    k = e.number_of_images
    alg = e.algorithm



#    if alg == 'random' :
#        samp = random.sample(objs, k)
    
#    elif alg == 'dirchlet' :
    #if alg == 'dirchlet' :
    if alg.startswith('dirchlet') :
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

    elif alg.startswith('auer') or alg == 'random' or (alg.startswith('pichunter') and e.iterations == 0) :
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
                    
    elif alg.startswith('pichunter') :
        basemeasures = request.session['basemeasures']
        samp = []
        tmp = map(lambda x : (basemeasures[x], x), range(len(basemeasures)))
        tmp.sort(reverse=True)
        for x,y in tmp[:k] :
            samp.append(objs[y])
        
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
                        'random' : int(alg == 'random'),
                        'target' : '/site_media/' + e.target.filename
                    }))
    
    print "\tdo_search(): %d seconds" % (int(time.time() - start_search))
    return HttpResponse(html)

