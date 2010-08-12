from django.http import HttpResponse
from django.template.loader import get_template
from django.template import Context
from gallery.models import Annotation, AnnotationOwner, AnnotationObject, Experiment, ExperimentInfo
import random

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
    target = random.choice(objs)
    
    request.session.flush()
    
    e = Experiment()
    e.sessionid = request.session.session_key
    e.iterations = 0
    e.target = target
    e.save()
    
    html = t.render(Context({'image' : '/site_media/' + target.filename}))
    
    return HttpResponse(html)

def do_search(request, number, state):
    e = Experiment.objects.get(sessionid=request.session.session_key)
#    html = "<html><body><p>looking for %s</p></body></html>" % e.target.filename
#    return HttpResponse(html)

    if state != 'start' :
        ei = ExperimentInfo.objects.get(experiment=e, iteration=e.iterations-1)
        ei.selection = state
        ei.save()
        print "saved %s" % state

    t = get_template('gallery.html')
    objs = Annotation.objects.all()
    samp = random.sample(objs, int(number))

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
        images.append({ 'image': "/site_media/%s" % s.filename, \
                        'link': "/search/%s/%s/" % (number, s.filename)})
    
    html = t.render(Context({'image_list' : images}))
    
    return HttpResponse(html)




