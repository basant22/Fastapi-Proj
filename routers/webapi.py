from fastapi import FastAPI,Depends,HTTPException,Header,UploadFile,File,Request,status,APIRouter
# rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from bs4 import BeautifulSoup
import requests
from time import time

webrouter = APIRouter(prefix='/v1/web/api', tags=['web'])
Cache_data = []
last_fetch = 0    

@webrouter.get("/news")
def get_news(page:int=1,limit:int=5):
    url = "https://news.ycombinator.com/"   
    response = requests.get(url)
    soup = BeautifulSoup(response.text,"html.parser")
    title=[]
    
   
    for item in soup.find_all('span', class_="titleline"):
            title.append(item.text)
        
    
       
    #pagination logic
    start = (page-1)*limit
    end = start+limit
    if len(title) > 5:
       
        return{
            "page":page,
            "limit":limit,
            "total":len(title),
            "data":title[start:end]
        }    
        
    else:
        return{
            "page":page,
            "limit":limit,
            "total":len(title),
            "data":title[start:end]
        }  
  
@webrouter.get("/cachednews")
def get_cached_news(page:int=1,limit:int=5):
    global Cache_data,last_fetch
    url = "https://news.ycombinator.com/"   
    response = requests.get(url)
    soup = BeautifulSoup(response.text,"html.parser")
    title=[]
    start = time.time()
    if time.time() - last_fetch > 60:
       
        print("Fresh start")
        Cache_data=[
          item.text for item in soup.find_all('span', class_="titleline")
        ]
    
       
        last_fetch = time.time()
        time_taken = round(last_fetch-start,4) 
        print("time taken",time_taken)
        return{
            "time taken":time_taken,
            "data":Cache_data
        }    
       
    else:
        print("cached start")
        end = time.time()
        time_taken = round(end-start,4) 
        print("time taken",time_taken)
        return{
            "time taken":time_taken,
            "data":Cache_data
        }    
