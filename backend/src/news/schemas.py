from pydantic import BaseModel


class NewsRequest(BaseModel):
    prompt: str


class NewsResponse(BaseModel):
    title: str
    content: str
    upvotes: int


class NewsSumaryRequestSchema(BaseModel):
    content: str


class PromptRequest(BaseModel):
    prompt: str


class NewsSumaryCustomModelSchema(BaseModel):
    content: str = "注意降溫！三立氣象主播黃家緯指出，本週天氣主要是3階段變化，明（10）日會和今日類似，氣溫稍暖、降雨偏少；週三至週五（11日至13日）水氣來襲，降雨增加；週六（14日）轉乾冷，那時有一波冷氣團南下，不排除達強烈大陸冷氣團等級，可能讓北部空曠地區低溫下探10度、中南部的整體氣溫也會下降2度左右。黃家緯指出，今（9）日東北季風減弱，各地稍稍回暖，也有機會看到陽光露臉；白天氣溫回升快，但日夜溫差也較大，例如平地的最低溫11.9度出現在苗栗、白天高溫則是25度，溫差逾10度。降雨方面，今日降雨量偏少，主要是在基隆北海岸、宜蘭山區有零星降雨。"
