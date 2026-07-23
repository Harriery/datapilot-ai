"""
Bu dosya, geçici session ve konuşma geçmişi yönetimini içerir.

- Session'lara ait konuşma geçmişlerini bellekte saklar.
- Konuşma geçmişinin kontrolsüz büyümesini önler.
- History temizleme işlemlerini yönetir.

Not:
Bu veriler şu anda RAM'de tutulur.
Uygulama yeniden başladığında bütün session'lar silinir.
"""

conversation_history = {}               #Her session_id, kendi konuşma listesini gösterecek.
                                        #{
                                        #    "session-1": [...],
                                        #    "session-2": [...],
                                        #} seklinde gorunecek
                                        #bütün kullanıcıların konuşmalarını tutan büyük dolap: {
                                        #{
                                        #     "yasin-1": [...],
                                        #    "ayse-1": [...],
                                        #}

MAX_HISTORY_MESSAGES = 10

#  # BU FONK ISTEKLERIN VE CEVAPLARIN SON 10unu TUTMAK ICIN KULLANILIR
#  EGER YENI BIR ISTEK OLDUGUNDA YANI 11 OLDUGUNDA EN ESKI MESAJI SILER
#  History sınırı aşılırsa en eski mesajları siler.
def trim_history(history):                    
    while len(history) > MAX_HISTORY_MESSAGES:   #if kullansaydik sadece 1 kez silerdi.
        history.pop(0)
