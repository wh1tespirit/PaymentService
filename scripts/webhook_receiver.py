from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    print("Webhook received:", await request.json(), flush=True)
    return {"ok": True}
