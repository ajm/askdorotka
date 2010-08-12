from django.db import models

LEN = 128

# Create your models here.
class AnnotationOwner(models.Model) :
    flickrid = models.CharField(max_length=LEN)
    name = models.CharField(max_length=LEN)

    def __unicode__(self):
        return u'AnnotationOwner: %s %s' % (self.flickrid, self.name)

class Annotation(models.Model) :
    filename = models.CharField(max_length=LEN)
    folder = models.CharField(max_length=LEN)
    owner = models.ForeignKey(AnnotationOwner)
    width = models.IntegerField()
    height = models.IntegerField()
    depth = models.IntegerField()
    segmented = models.BooleanField()

    def __unicode__(self):
        return u'Annotation: %s %d %d' % (self.filename, self.width, self.height)
    
class AnnotationObject(models.Model) :
    name = models.CharField(max_length=LEN)
    POSE_CHOICES = (
        ('L', 'Left'),
        ('R', 'Right'),
        ('F', 'Frontal'),
        ('B', 'Rear'),
        ('U', 'Unspecified')
    )
    pose = models.CharField(max_length=1, choices=POSE_CHOICES)
    truncated = models.BooleanField()
    difficult = models.BooleanField()
    xmin = models.FloatField()
    ymin = models.FloatField()
    xmax = models.FloatField()
    ymax = models.FloatField()
    parent_annotation = models.ForeignKey(Annotation)

    def __unicode__(self):
        return u'AnnotationObject: %s %s %d %d %d %d' % \
            (self.name, self.pose, self.xmin, self.xmax, self.ymin, self.ymax)

class Experiment(models.Model) :
    sessionid = models.CharField(max_length=LEN)
    target = models.ForeignKey(Annotation)
    iterations = models.PositiveIntegerField()

    def __unicode__(self) :
        return u'Experiment: %s %s' % (self.sessionid, self.target.filename)
    
class ExperimentInfo(models.Model) :
    experiment = models.ForeignKey(Experiment)
    iteration = models.PositiveIntegerField()
    selection = models.CharField(max_length=LEN)
    options = models.ManyToManyField(Annotation)
    
    def __unicode__(self):
        return u'ExperimentInfo: %d %s' % (self.iteration, self.selection)

