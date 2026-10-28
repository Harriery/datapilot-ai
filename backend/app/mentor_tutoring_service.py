"""Scaffold an already-validated pending inspection without assigning a new one."""
import re
import unicodedata


def normalized(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(c)).replace('ı', 'i').replace('’', "'")


def explicit_code_requested(message: str) -> bool:
    text = normalized(message)
    if re.search(r'kod\w*\s+(?:gosterme\w*|verme\w*|yazma\w*|paylasma\w*)|'
                 r'cozum\w*\s+(?:verme\w*|gosterme\w*|soyleme\w*)|'
                 r'without\s+(?:giving\s+(?:me\s+)?)?(?:(?:any|the)\s+)?(?:code|solution)|no\s+(?:(?:python|sql)\s+)?(?:code|solution)|'
                 r'(?:do not|don\x27t)\s+(?:show|give|write|provide).{0,20}(?:code|solution)|'
                 r'zonder\s+(?:de\s+)?(?:code|oplossing)|geen\s+(?:code|oplossing)|'
                 r'(?:toon|geef)\s+de\s+code\s+niet', text):
        return False
    return bool(re.search(r'\bkodu\s+(?:goster|yaz|ver)\b|\bkodu\s+(?:gosterebilir|gosterir|yazabilir|verebilir)\s*mi\w*\b|\bkod\s+ornegi\s+ver\b|'
                          r'\b(?:show|give)\s+(?:me\s+)?(?:the\s+)?code\b|'
                          r'\b(?:toon|geef)\s+de\s+code\b|\blaat\s+de\s+code\s+zien\b', text))


def support_requested(message: str) -> bool:
    if explicit_code_requested(message):
        return True
    text = normalized(message)
    return bool(re.search(r'nasil\s+(?:yap|yaz|uygula)|nasil.{0,40}bilmiyorum|'
                          r'ipucu\s+ver|anlamadim|ne\s+yapacagimi\s+bilmiyorum|daha\s+(?:basit|ayrintili|detayli|kolay)|'
                          r'(?:don\x27t|do not)\s+know\s+(?:how|what to do)|how\s+(?:do|can)\s+i|'
                          r'give\s+me\s+a\s+hint|still\s+don\x27t\s+understand|'
                          r'explain\s+(?:it\s+)?more\s+simply|'
                          r'weet\s+niet\s+hoe|hoe\s+(?:doe|kan|moet)\s+ik|'
                          r'geef\s+(?:me\s+)?een\s+hint|nog\s+steeds\s+niet|eenvoudiger|simpeler', text))



def teaching_code_mode(message: str) -> str:
    """none=prose; example=analogous snippet; direct=learner's task code."""
    text = normalized(message)
    if re.search(
        r'kod\w*\s+(?:gosterme\w*|verme\w*|yazma\w*|paylasma\w*)|'
        r'cozum\w*\s+(?:verme\w*|gosterme\w*|soyleme\w*)|'
        r'without\s+(?:giving\s+(?:me\s+)?)?(?:(?:any|the)\s+)?(?:code|solution)|'
        r'no\s+(?:(?:python|sql)\s+)?(?:code|solution)|'
        r'(?:do not|don\x27t)\s+(?:show|give|write|provide).{0,20}(?:code|solution)|'
        r'zonder\s+(?:de\s+)?(?:code|oplossing)|geen\s+(?:code|oplossing)|'
        r'(?:toon|geef)\s+de\s+code\s+niet',
        text,
    ):
        return 'none'
    if re.search(r'\bkod\s+ornegi\b|\bcode\s+example\b|\bvoorbeeldcode\b', text):
        return 'example'
    if explicit_code_requested(message):
        return 'direct'
    if re.search(
        r'\bnasil\b|\bhow\s+(?:do|can|should)\s+i\b|'
        r'\bhoe\s+(?:doe|kan|moet)\s+ik\b', text,
    ):
        return 'example'
    return 'none'
