class LanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # التحقق مما إذا كان المستخدم قد مرر اللغة عبر الـ URL
        lang = request.GET.get('lang')
        if lang in ['ar', 'en']:
            request.session['lang'] = lang
        
        # إذا لم تكن مخزنة مسبقاً، اجعلها العربية كافتراضي
        if 'lang' not in request.session:
            request.session['lang'] = 'ar'
            
        response = self.get_response(request)
        return response