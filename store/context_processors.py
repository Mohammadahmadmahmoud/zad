def language_processor(request):
    lang = request.session.get('lang', 'ar')
    return {
        'lang': lang,
        'CURRENT_LANG': lang,
    }