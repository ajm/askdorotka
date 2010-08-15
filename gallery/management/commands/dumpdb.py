from django.core.management.base import BaseCommand, CommandError
from askdorotka.gallery.models import Annotation, AnnotationObject, Experiment, ExperimentInfo

class Command(BaseCommand) :
    args = ''
    help = 'dumps experimental database tables to stdout'

    def handle(self, *args, **options) :
        experiments = Experiment.objects.all()

        for e in experiments :
            if e.finished :
                if e.random :
                    x = "random"
                else :
                    x = "dirichlet"
                print "Experiment\t%s\t%d\t%d\t%s" % (x, e.number_of_images, e.iterations, e.target.filename)
                info = ExperimentInfo.objects.filter(experiment=e)
                data = {}
                for i in info :
                    data[int(i.iteration)] = (i.selection, ','.join(map(lambda x : x.filename, i.options.all())))
                for i in sorted(data.keys()) :
                    print "%d\t%s" % (i, "\t".join(data[i]))

