
from mycouch.views.main import main, index

routes = [
    ((main, ''),
        ('/', index),
        ('/<name>', index),
    )
]
