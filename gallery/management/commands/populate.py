from django.core.management.base import BaseCommand, CommandError
from askdorotka.gallery.models import Annotation, AnnotationObject, AnnotationOwner, AnnotationFeature

from xml.dom.minidom import parse
import glob, os, math, copy

class Command(BaseCommand) :
    args = '<directory containing xml annotations>'
    help = 'populates database with content of XML files'

    def process_annotation(self, ele) :
        err = False
        a = Annotation()
        owner = None
        objects = []
        
        children = [e for e in ele.childNodes if e.nodeType == e.ELEMENT_NODE]
        
        for c in children :
            if c.nodeName == 'folder' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                a.folder = c.childNodes[0].nodeValue
            
            elif c.nodeName == 'filename' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                a.filename = c.childNodes[0].nodeValue

            elif c.nodeName == 'source' :
                self.process_source(c) # ???

            elif c.nodeName == 'owner' :
                owner = self.process_owner(c)
            
            elif c.nodeName == 'size' :
                width,height,depth = self.process_size(c)
                
                a.width = width
                a.height = height
                a.depth = depth

            elif c.nodeName == 'segmented' :
                if len(c.childNodes) != 1 :
                    err = True
                    break
                
                if c.childNodes[0].nodeValue == '0':
                    a.segmented = False
                else :
                    a.segmented = True

            elif c.nodeName == 'object' :
                objects += self.process_object(c)

            else :
                raise CommandError('could not process node of type: %s' % c.nodeName)

            if err :
                raise CommandError('%s node was of length %d' % (c.nodeName, len(c.childNodes)))

        
        # check whether owner exists
        owners = AnnotationOwner.objects.filter(flickrid=owner.flickrid)
        if len(owners) == 0 :
            owner.save()
#            print str(owner)
        else :
            owner = owners[0]
        
        a.owner = owner
        a.save()
#        print str(a)

        for o in objects :
            o.parent_annotation = a
            o.area = (o.xmax - o.xmin) * (o.ymax - o.ymin)
            o.save()
#            print str(o)

        self.normalise2(a, objects)

    def normalise2(self, annot, objs) :
        area = float(annot.width * annot.height)
        
        for o in objs :
            a = AnnotationFeature()
            a.name = o.name
            a.parent = annot
            a.value = o.area / area
            a.save()

    def normalise1(self, annot, objs) :
        total = {}
        labels = list(set(map(lambda x : x.name, objs)))
        #labels = ['aeroplane','bicycle','bird','boat','bottle','bus','car','cat','chair','cow','diningtable','dog','food','hand','head','horse','motorbike','person','pottedplant','sheep','sofa','train','tvmonitor'] :
        for i in labels :
            total[i] = 0

        for o in objs :
            total[o.name] += o.area
            
        fac = math.sqrt(float(sum(map(lambda x : x ** 2, total.values()))))

        for k,v in total.iteritems() :
            if v != 0 :
                a = AnnotationFeature()
                a.name = k
                a.value = v / fac
                a.parent = annot
                a.save()

    def process_object(self, ele) :
        err = False
        parts = []
        tmp = None
        a = AnnotationObject()
        children = [e for e in ele.childNodes if e.nodeType == e.ELEMENT_NODE]

        for c in children :
            if c.nodeName == 'name' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                a.name = c.childNodes[0].nodeValue

            elif c.nodeName == 'pose' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                pose = c.childNodes[0].nodeValue
                tmp = pose
                if pose == 'Left' :
                    a.pose = 'L'
                elif pose == 'Right' :
                    a.pose = 'R'
                elif pose == 'Rear' :
                    a.pose = 'B'
                elif pose == 'Frontal' :
                    a.pose = 'F'
                elif pose == 'Unspecified' :
                    a.pose = 'U'

            elif c.nodeName == 'truncated' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                if c.childNodes[0].nodeValue == '0' :
                    a.truncated = False
                else :
                    a.truncated = True

            elif c.nodeName == 'difficult' :
                if len(c.childNodes) != 1 :
                    err = True
                    break
                
                if c.childNodes[0].nodeValue == '0' :
                    a.difficult = False 
                else :
                    a.difficult = True

            elif c.nodeName == 'bndbox' :
                xmin,xmax,ymin,ymax = self.process_bndbox(c)
                a.xmin = xmin
                a.xmax = xmax
                a.ymin = ymin
                a.ymax = ymax

            elif c.nodeName == 'part' :
                parts.append(self.process_part(c))

            else :
                raise CommandError('could not process node of type: %s' % c.nodeName)

            if err :
                raise CommandError('%s node was of length %d' % (c.nodeName, len(c.childNodes)))

        # treat pose as first-class feature
        p = copy.copy(a)
        p.name = tmp
        parts.append(a)
        parts.append(p)

        return parts
    
    def process_owner(self, ele) :
        err = False
        children = [e for e in ele.childNodes if e.nodeType == e.ELEMENT_NODE]
        a = AnnotationOwner()

        for c in children :
            if c.nodeName == 'flickrid':
                if len(c.childNodes) != 1 :
                    err = True
                    break

                a.flickrid = c.childNodes[0].nodeValue
            
            elif c.nodeName == 'name':
                if len(c.childNodes) != 1 :
                    err = True
                    break
                
                a.name = c.childNodes[0].nodeValue

            else :
                raise CommandError('could not process node of type: %s' % c.nodeName)

            if err :
                raise CommandError('%s node was of length %d' % (c.nodeName, len(c.childNodes)))

        return a

    def process_source(self, ele) :
        pass

    def process_part(self, ele) :
        children = [e for e in ele.childNodes if e.nodeType == e.ELEMENT_NODE]
        a = AnnotationObject()
        err = False

        for c in children :
            if c.nodeName == 'name' :
                if len(c.childNodes) != 1 :
                    err = True
                    break
                a.name = c.childNodes[0].nodeValue

            elif c.nodeName == 'bndbox' :
                xmin,xmax,ymin,ymax = self.process_bndbox(c)
                a.xmin = xmin
                a.xmax = xmax
                a.ymin = ymin
                a.ymax = ymax

            else :
                raise CommandError('could not process node of type: %s' % c.nodeName)

            if err :
                raise CommandError('%s node was of length %d' % (c.nodeName, len(c.childNodes)))

        return a

    def process_size(self, ele) :
        err = False
        w = None
        h = None
        d = None
        children = [e for e in ele.childNodes if e.nodeType == e.ELEMENT_NODE]
        
        for c in children :
            if c.nodeName == 'width' :
                if len(c.childNodes) != 1 :
                    err = True
                    break
            
                w = int(c.childNodes[0].nodeValue)
            
            elif c.nodeName == 'height' :
                if len(c.childNodes) != 1 :
                    err = True
                    break
            
                h = int(c.childNodes[0].nodeValue)
            
            elif c.nodeName == 'depth' :
                if len(c.childNodes) != 1 :
                    err = True
                    break
            
                d = int(c.childNodes[0].nodeValue)
            
            else :
                raise CommandError('could not process node of type: %s' % c.nodeName)

            if err :
                raise CommandError('%s node was of length %d' % (c.nodeName, len(c.childNodes)))

        if w == None or h == None or d == None :
            raise CommandError('size element did not contain all of width, height and depth')

        return w,h,d
    
    def process_bndbox(self, ele) :
        err = False
        xmin = None
        xmax = None
        ymin = None
        ymax = None
        children = [e for e in ele.childNodes if e.nodeType == e.ELEMENT_NODE]

        for c in children :
            if c.nodeName == 'xmin' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                xmin = float(c.childNodes[0].nodeValue)
            elif c.nodeName == 'xmax' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                xmax = float(c.childNodes[0].nodeValue)
            elif c.nodeName == 'ymin' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                ymin = float(c.childNodes[0].nodeValue)
            elif c.nodeName == 'ymax' :
                if len(c.childNodes) != 1 :
                    err = True
                    break

                ymax = float(c.childNodes[0].nodeValue)
            else :
                raise CommandError('could not process node of type: %s' % c.nodeName)

            if err :
                raise CommandError('%s node was of length %d' % (c.nodeName, len(c.childNodes)))
        
        if xmin == None or xmax == None or ymin == None or ymax == None :
            raise CommandError('bndbox element did not contain all of xmin, xmax, ymin, ymax')

        return xmin,xmax,ymin,ymax
    
    def featuredict(self, annotation) :
        d = {}
        for f in AnnotationFeature.objects.filter(parent=annotation) :
            d[f.name] = f.value

        return d

    def calc_distance(self, annotation1, annotation2) :
        features1 = self.featuredict(annotation1)
        features2 = self.featuredict(annotation2)

        total = 0.0
        for k in set(features1.keys() + features2.keys()) :
            f1 = features1.get(k, 0.0)
            f2 = features2.get(k, 0.0)

            total += ((f1 - f2) ** 2)

        return total
    
    def handle(self, *args, **options) :
        if len(args) != 1 :
            raise CommandError("populate command needs xml dir as argument")

        path = args[0]

        xmlfiles = glob.glob(os.path.join(path, '*.xml'))
        for filename in xmlfiles :
            print "processing: %s" % filename

            f = open(filename)
            doc = parse(f).documentElement
            
            self.process_annotation(doc)

        return 
        # build distance cache
        a = Annotation.objects.all()
        for i in range(len(a)) :
            print "%s" % a[i].filename
            for j in range(i+1, len(a)) :
                d = self.calc_distance(a[i],a[j])
                a1 = AnnotationDistance()
                a1.src = a[i].filename
                a1.dst = a[j].filename
                a1.distance = d
                a1.save()
                a2 = AnnotationDistance()
                a2.src = a[j].filename
                a2.dst = a[i].filename
                a2.distance = d
                a2.save()
                print "\t%s --> %s = %f (%s)" % (a[i].filename, a[j].filename, d, str(d == 0.0))

