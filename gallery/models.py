from django.db import models

LEN = 128

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
    used = models.BooleanField()

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
    area = models.FloatField()

    def __unicode__(self):
        return u'AnnotationObject: %s %s %d %d %d %d' % \
            (self.name, self.pose, self.xmin, self.xmax, self.ymin, self.ymax)

class AnnotationFeature(models.Model) :
    name = models.CharField(max_length=LEN)
    value = models.FloatField()
    parent = models.ForeignKey(Annotation)

    def __unicode__(self):
        return u'AnnotationFeature: %s %f %s' % (self.name, self.value, self.parent)

class Experiment(models.Model) :
    # web variables
    sessionid = models.CharField(max_length=LEN)
    # experiment variables
    target = models.ForeignKey(Annotation)
    number_of_images = models.PositiveIntegerField()
    finished = models.BooleanField()
#    random = models.BooleanField()
    iterations = models.PositiveIntegerField()
    algorithm = models.CharField(max_length=LEN)
    # dirchlet variables
    alpha = models.PositiveIntegerField()
    count = models.PositiveIntegerField()
    
    def __unicode__(self) :
        return u'Experiment: %s %s' % (self.sessionid, self.target.filename)

class ExperimentInfo(models.Model) :
    experiment = models.ForeignKey(Experiment)
    iteration = models.PositiveIntegerField()
    selection = models.CharField(max_length=LEN)
    options = models.ManyToManyField(Annotation)
    
    def __unicode__(self):
        return u'ExperimentInfo: %d %s' % (self.iteration, self.selection)

