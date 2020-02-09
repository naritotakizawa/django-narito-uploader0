import io
import zipfile
from django import forms
from django.core.exceptions import PermissionDenied
from django.http import Http404, FileResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, resolve_url, get_object_or_404
from django.urls import reverse_lazy
from django.utils.cache import patch_response_headers
from django.views import generic
from .models import Composite


class PathTop(generic.CreateView):
    model = Composite
    fields = ('name', 'is_dir', 'src', 'zip_depth')
    success_url = reverse_lazy('nuploader0:path')
    template_name = 'nuploader0/composite_list.html'

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['add_form'] = context['form']
        context['composite_list'] = Composite.objects.filter(parent__isnull=True).order_by('name')
        return context


class Path(generic.TemplateView):
    template_name = 'nuploader0/composite_list.html'
    model = Composite
    add_fields = fields = ('name', 'is_dir', 'src', 'zip_depth')
    update_fields = ('name', 'parent', 'zip_depth')
    url_name = 'nuploader0:path'
    path_url_kwarg = 'request_path'

    def get_request_path(self):
        return self.kwargs.get(self.path_url_kwarg, '')

    def make_clean_path_list(self):
        request_path = self.get_request_path()
        return [path for path in request_path.split('/') if path]

    def get_prev_request_path(self):
        path_list = self.make_clean_path_list()
        path_list.pop()
        return '/'.join(path_list)

    def get_prev_url(self):
        # urls.pyのURL定義では末尾にスラッシュがない。前URLは基本的にディレクトリなので、末尾に/を足す必要がある。
        prev_request_path = self.get_prev_request_path()
        if prev_request_path:
            kwargs = {self.path_url_kwarg: prev_request_path}
            url = resolve_url(self.url_name, **kwargs)
        else:
            url = resolve_url(self.url_name)

        if not url.endswith('/'):
            url += '/'
        return url

    def get_sql_kwargs(self):
        path_list = self.make_clean_path_list()
        i = 0
        kwargs = {}
        for path in path_list[::-1]:
            arg_name = 'parent__' * i + 'name'
            kwargs[arg_name] = path
            i += 1
        arg_name = 'parent__' * i + 'isnull'
        kwargs[arg_name] = True
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['composite'] = self.composite
        context['composite_list'] = self.composite.composite_set.all().order_by('name')

        if hasattr(self, 'add_form'):
            context['add_form'] = self.add_form
        else:
            context['add_form'] = self.get_add_form()

        if hasattr(self, 'update_form'):
            context['update_form'] = self.update_form
        else:
            context['update_form'] = self.get_update_form()

        return context

    def get_object(self):
        composite = self.composite = self.model.objects.select_related('parent').get(**self.get_sql_kwargs())
        return composite

    def get_add_form_class(self):
        if hasattr(self, 'add_form_class'):
            return self.add_form_class
        return forms.modelform_factory(self.model, fields=self.add_fields)

    def get_add_form(self):
        form_class = self.get_add_form_class()
        kwargs = {}
        # 追加ボタンを押したときだけ、追加フォームにPOSTデータを紐づける
        # これをしないと、更新フォームと処理が競合するっぽい
        if self.request.POST.get('type') == 'add':
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        form = self.add_form = form_class(**kwargs)
        return form

    def get_update_form_class(self):
        if hasattr(self, 'update_form_class'):
            return self.update_form_class
        return forms.modelform_factory(self.model, fields=self.update_fields)

    def get_update_form(self):
        form_class = self.get_update_form_class()
        kwargs = {'instance': self.composite}
        # 更新ボタンを押したときだけ、更新フォームにPOSTデータを紐づける
        # これをしないと、追加フォームと処理が競合するっぽい
        if self.request.POST.get('type') == 'update':
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        form = self.update_form = form_class(**kwargs)
        return form

    def get(self, request, *args, **kwargs):
        try:
            composite = self.get_object()
        except Composite.DoesNotExist:
            raise Http404
        else:
            if composite.is_dir:
                return self.get_dir()
            else:
                return self.get_file()

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied

        kind = request.POST['type']
        if kind == 'delete':
            return self.post_delete(request, *args, **kwargs)
        elif kind == 'add':
            return self.post_add(request, *args, **kwargs)
        elif kind == 'update':
            return self.post_update(request, *args, **kwargs)
        else:
            return self.get(request, *args, **kwargs)

    def get_dir(self):
        context = self.get_context_data()
        return render(self.request, self.template_name, context)

    def get_file(self):
        response = FileResponse(self.composite.src)
        patch_response_headers(response, 60*60*24*7)
        return response

    def post_delete(self, request, *args, **kwargs):
        try:
            composite = self.get_object()
        except Composite.DoesNotExist:
            raise Http404
        else:
            composite.delete()

        return redirect(self.get_prev_url())

    def post_add(self, request, *args, **kwargs):
        parent = self.get_object()
        form = self.get_add_form()
        form.instance.parent = parent  # parentが先にないと、モデルのcleanでの同名ファイルの確認ができない
        if form.is_valid():
            form.save()
            return redirect(self.request.get_full_path())

        context = self.get_context_data()
        return render(self.request, self.template_name, context)

    def post_update(self, request, *args, **kwargs):
        composite = self.get_object()
        form = self.get_update_form()
        if form.is_valid():
            form.save()
            return redirect(self.get_prev_url())

        context = self.get_context_data()
        return render(self.request, self.template_name, context)


def download_zip(request, pk):
    composite = get_object_or_404(Composite, pk=pk)
    if not composite.zip_depth:
        return HttpResponseBadRequest('ZIPが許可されているファイル・ディレクトリではありません。')

    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{composite.name}.zip"'
    zip_file = zipfile.ZipFile(response, 'w')
    if not composite.is_dir:
        zip_file.writestr(composite.name, composite.src.read())
    else:
        walk_and_write(composite, zip_file, composite.zip_depth)

    return response


def walk_and_write(composite, zip_file, count, dir_name=''):
    """再帰的にCompositeを走査し、zipファイルに書き込んでいく"""
    dirs = []
    for composite in composite.composite_set.all():
        if composite.is_dir:
            dirs.append(composite)
        else:
            zip_file.writestr(dir_name + composite.name, composite.src.read())
    count -= 1

    if count:
        for composite in dirs:
            walk_and_write(composite, zip_file, count, f'{dir_name}{composite.name}/')
