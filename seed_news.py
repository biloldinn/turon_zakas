
from database import add_news
from datetime import datetime

def seed_news():
    # Adding the adapted Lidl news for Turon
    title = "Turon O'quv Markazi: Xodimlar uchun yangi imtiyozlar"
    content = """Turon O'quv Markazi o'z xodimlarining hayotini yaxshilashda davom etmoqda. 

Biz jamoamiz uchun yangi imtiyozlar paketini e'lon qilamiz:
1. Qon topshiruvchi xodimlarimiz uchun qo'shimcha dam olish kunlari.
2. Kasbiy va shaxsiy rivojlanish uchun onlayn o'quv platformasiga bepul kirish.
3. Psixologik va huquqiy qo'llab-quvvatlash xizmati.

Sizning mehnatining va sodiqligingiz biz uchun juda qadrli!"""
    
    add_news(title, content, "Sistema")
    print("Namuna yangilik muvaffaqiyatli qo'shildi!")

if __name__ == "__main__":
    seed_news()
