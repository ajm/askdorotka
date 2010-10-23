from django.core.management.base import BaseCommand, CommandError
from askdorotka.gallery.models import Annotation, AnnotationObject, Experiment, ExperimentInfo, AnnotationFeature

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


class Command(BaseCommand) :
    args = ''
    help = 'dumps experimental database tables to st'

    def handle(self, *args, **options) :
        experiments = Experiment.objects.all()

        for e in experiments :
            if e.finished :
                #avg = sum(map(lambda x : calc_distance2(e.target, x), Annotation.objects.all())) / float(len(Annotation.objects.all()))
                #print "Experiment\t%s\t%d\t%d\t%s\t%f" % (e.algorithm, e.number_of_images, e.iterations, e.target.filename, avg)
                print "Experiment\t%s\t%d\t%d\t%s" % (e.algorithm, e.number_of_images, e.iterations, e.target.filename)
                info = ExperimentInfo.objects.filter(experiment=e)
                data = {}
                for i in info :
                    data[int(i.iteration)] = (\
                        str(calc_distance2(e.target, Annotation.objects.get(filename=i.selection))), \
                        ','.join(map(lambda x : str(calc_distance2(e.target, Annotation.objects.get(filename=x.filename))), i.options.all())))
                for i in sorted(data.keys()) :
                    print "%d\t%s" % (i, "\t".join(data[i]))

