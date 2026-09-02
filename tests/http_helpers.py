import io


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
