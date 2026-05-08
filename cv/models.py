from django.db import models
from django.utils import timezone

class Device(models.Model):
    device_id = models.CharField(max_length=255, unique=True)
    
    # გადახდილი ჩამოტვირთვების რაოდენობა
    paid_downloads_balance = models.IntegerField(default=0)
    
    # ბოლო გადახდის ზუსტი დრო (DateTimeField - აუცილებელია 24 საათისთვის)
    last_payment_date = models.DateTimeField(null=True, blank=True)

    def can_download(self):
        if not self.last_payment_date or self.paid_downloads_balance <= 0:
            return False
        
        # ვამოწმებთ გავიდა თუ არა 24 საათი გადახდიდან
        expiry_time = self.last_payment_date + timezone.timedelta(hours=24)
        
        if timezone.now() > expiry_time:
            # თუ ვადა გავიდა, ვანულებთ ბალანსს
            if self.paid_downloads_balance > 0:
                self.paid_downloads_balance = 0
                self.save()
            return False
            
        return self.paid_downloads_balance > 0

    def increment_download(self):
        """აკლებს ბალანსს ჩამოტვირთვისას"""
        if self.paid_downloads_balance > 0:
            self.paid_downloads_balance -= 1
            self.save()

    def add_paid_limit(self, count=3):
        """ამატებს ჩამოტვირთვებს და ანახლებს დროს"""
        self.paid_downloads_balance += count
        self.last_payment_date = timezone.now()
        self.save()

    def __str__(self):
        return f"Device: {self.device_id} | Balance: {self.paid_downloads_balance}"