from django.core.management.base import BaseCommand, CommandError
from askdorotka.gallery.models import Annotation, AnnotationObject, AnnotationFeature

class Command(BaseCommand) :
    args = ''
    help = 'dumps features from database to stdout'

    def handle(self, *args, **options) :

        labels = ['aeroplane','bicycle','bird','boat','bottle','bus','car','cat','chair','cow','diningtable','dog','food','hand','head','horse','motorbike','person','pot    tedplant','sheep','sofa','train','tvmonitor','Left','Right','Frontal','Rear','Unspecified']

        annotations = Annotation.objects.all()

        for a in annotations :
            features = AnnotationFeature.objects.filter(parent=a)
            tmp = {}
            for f in features :
                tmp[f.name] = f.value
            for l in labels :
                print "%f" % tmp.get(l, 0.0),
            print ""
        
