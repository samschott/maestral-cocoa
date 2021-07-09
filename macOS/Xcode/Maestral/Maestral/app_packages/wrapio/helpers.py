import inspect
import collections


__all__ = ()


def register(apply, name, check = callable):

    def wrapper(value):
        return apply(name, value)

    if not check(name):
        return wrapper

    (name, value) = (name.__name__, name)

    return wrapper(value)


def subconverge(level, name, values):

    stack = inspect.stack()
    items = stack[level + 1].frame.f_locals.items()

    product = []
    values = list(values)

    for (key, check) in reversed(items):
        for value in values:
            if check is value:
                break
        else:
            continue
        values.remove(value)
        product.insert(0, key)

    name = ''.join(name.title().replace(' ', ''))

    return collections.namedtuple(name, product)
