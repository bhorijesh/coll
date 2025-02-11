class NotificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Clear notification after it's been displayed
        if 'notification' in request.session:
            del request.session['notification']
        
        return response