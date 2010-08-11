from django.contrib import admin
from askdorotka.gallery.models import Annotation, AnnotationOwner, AnnotationObject

admin.site.register(AnnotationOwner)
admin.site.register(Annotation)
admin.site.register(AnnotationObject)
