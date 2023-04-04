import gc

import hiredis


def test_reader_gc():
    class A:
        def __init__(self):
            self.reader = hiredis.Reader(replyError=self.reply_error)

        def reply_error(self, error):
            return Exception()

    A()
    gc.collect()

    assert not any(isinstance(o, A) for o in gc.get_objects()), "Referent was not collected"
