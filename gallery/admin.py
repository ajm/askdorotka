from django.contrib import admin
from askdorotka.gallery.models import Annotation, AnnotationOwner, AnnotationObject, Experiment, ExperimentInfo

admin.site.register(AnnotationOwner)
admin.site.register(Annotation)
admin.site.register(AnnotationObject)
admin.site.register(Experiment)
admin.site.register(ExperimentInfo)
