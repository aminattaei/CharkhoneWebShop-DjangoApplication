import time
from locust import HttpUser, task # type: ignore

class QuickstartUser(HttpUser):
    
    @task
    def hello_world(self):
        self.client.get("/shop/product/شش-ارسال/")
        self.client.get("/shop/product/card-marriage/")