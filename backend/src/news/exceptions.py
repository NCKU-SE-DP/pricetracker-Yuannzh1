class ExtractFailure(ValueError):
    def __init__(self, message: str = "No keywords extracted from the provided prompt."):
        self.message = message
        super().__init__(self.message)


'''
class ParseFailure(AttributeError):
    def __init__(self, news_url: str, parse_err: Exception):
        self.message = f"HTML Parsing Error for {news_url}: {parse_err}"
        super().__init__(self.message)
'''
