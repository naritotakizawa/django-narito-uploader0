from django import template

register = template.Library()


@register.simple_tag
def create_composite_link(request, composite):
    path = f'{request.path_info}/{composite.name}/'.replace('//', '/')
    if not composite.is_dir:
        path = path[:-1]
    return path
