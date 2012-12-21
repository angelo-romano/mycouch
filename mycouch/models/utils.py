from sqlalchemy.ext.declarative import declared_attr


def declared(name, c):
    def fn(self):
        return c
    fn.__name__ = name
    return declared_attr(fn)
