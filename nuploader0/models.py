from django.db import models
from django.core.exceptions import ValidationError


class Composite(models.Model):
    name = models.CharField('名前', max_length=255)
    is_dir = models.BooleanField('ディレクトリか', default=True)
    src = models.FileField('ファイルソース', blank=True, null=True)
    parent = models.ForeignKey('self', verbose_name='親ディレクトリ', on_delete=models.CASCADE, blank=True, null=True, limit_choices_to={'is_dir': True})
    zip_depth = models.PositiveIntegerField('zipファイルの深さ', default=0)

    def __str__(self):
        if self.is_dir:
            return f'{self.pk} - {self.name}/'
        else:
            return f'{self.pk} - {self.name}'

    def get_display_name(self):
        if self.is_dir:
            return f'{self.name}/'
        else:
            return f'{self.name}'

    def clean(self):
        if self.parent == self:
            raise ValidationError('親ディレクトリが自分です')

        # /zip/1 といったURLは、zipファイル作成用URLなので、使わせない
        if self.parent is None and self.name == 'zip':
            raise ValidationError('最上位にzipという名前のディレクトリは作れません。')

        # 同名ファイル・ディレクトリがないかチェック。自分自身は許可するので、exclude(pk=self.pk)
        if Composite.objects.filter(parent=self.parent, name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError('同じ名前のファイル・ディレクトリが既に存在します')

        if not self.is_dir and not self.src:
            raise ValidationError('ファイルの時は、ファイルを添付してください')

        if self.is_dir and self.src:
            raise ValidationError('ディレクトリの時は、ファイルを添付しないでください')
