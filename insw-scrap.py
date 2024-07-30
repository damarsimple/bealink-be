import time, requests, json,glob, os

sets = set()
sets2 = set()

for i in open("a.csv", "r", encoding="utf-8").readlines():
    a = i.split(",")
    
    sets.add(str(a[0]).replace(".", ""))
    

for x in glob.glob("insw-batch/*.json"):
    print(x)
    data  = open(x, "r", encoding="utf-8")


    for i in json.loads(data.read())["data"][0]["result"]:
        x = i["_source"]["hs_code_format"]
        sets2.add(int(i["_id"]))
        sets.add(x)

length = len(sets)

print(length)

for i, hs_code in enumerate(sets):
    try:
        if os.path.isfile("insw/" + hs_code + ".json"): 
        
            # print("exists" + hs_code)
            continue
        # Set the URL and headers
        url = f"https://api.insw.go.id/api-prod-ba/ref/hscode/komoditas?hs_code={hs_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Authorization": "Basic aW5zd18yOmJhYzJiYXM2",
            "Origin": "https://insw.go.id",
            "Connection": "keep-alive",
            "Referer": "https://insw.go.id/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Priority": "u=0"
        }

        # Make the request
        response = requests.get(url, headers=headers)

        f = open("insw/" + hs_code + ".json", "w")
        f.write(
            json.dumps(
                response.json()["data"][0]
            )
        )

        print(f"{i}/{length} {hs_code}")
    except:continue