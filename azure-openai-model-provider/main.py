import json
import os
from typing import AsyncIterable

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from openai._streaming import Stream
from openai._types import NOT_GIVEN
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.embedding import Embedding
from openai import AzureOpenAI


endpoint = os.environ.get("OTTO8_AZURE_OPENAI_MODEL_PROVIDER_ENDPOINT", "")
api_key = os.environ.get("OTTO8_AZURE_OPENAI_MODEL_PROVIDER_API_KEY", "")
debug = os.environ.get("GPTSCRIPT_DEBUG", "false") == "true"
uri = "http://127.0.0.1:" + os.environ.get("PORT", "8000")

azure_client = AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version="2024-02-01")


def log(*args):
    if debug:
        print(*args)


app = FastAPI()

system: str = """
You are task oriented system.
You receive input from a user, process the input from the given instructions, and then output the result.
Your objective is to provide consistent and correct results.
You do not need to explain the steps taken, only provide the result to the given instructions.
You are referred to as a tool.
You don't move to the next step until you have a result.
"""


@app.middleware("http")
async def log_body(request: Request, call_next):
    body = await request.body()
    log("REQUEST BODY: ", body)
    return await call_next(request)


@app.get("/")
@app.post("/")
async def get_root():
    return uri


# Only needed when running standalone. With GPTScript, the `id` returned by this endpoint must match the model (deployment) you are passing in.
@app.get("/v1/models")
async def list_models() -> JSONResponse:
    return JSONResponse(content={"data": [{"id": "gpt-4", "name": "Your model"}]})


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.body()
    data = json.loads(data)

    tools = data.get("tools", NOT_GIVEN)

    if tools is not NOT_GIVEN:
        tool_choice = 'auto'
    else:
        tool_choice = NOT_GIVEN

    temperature = data.get("temperature", NOT_GIVEN)
    if temperature is not NOT_GIVEN:
        temperature = float(temperature)

    stream = data.get("stream", False)

    messages = data["messages"]
    messages.insert(0, {"content": system, "role": "system"})

    try:
        res: Stream[ChatCompletionChunk] | ChatCompletion = azure_client.chat.completions.create(model=data["model"],
                                                                                           messages=messages,
                                                                                           tools=tools,
                                                                                           tool_choice=tool_choice,
                                                                                           temperature=temperature,
                                                                                           stream=stream
                                                                                           )
        if not stream:
            return JSONResponse(content=jsonable_encoder(res))

        return StreamingResponse(convert_stream(res), media_type="application/x-ndjson")
    except Exception as e:
        try:
            log("Error occurred: ", e.__dict__)
            error_code = e.status_code
            error_message = e.message
        except:
            error_code = 500
            error_message = str(e)
        raise HTTPException(status_code=error_code, detail=f"Error occurred: {error_message}")


@app.post("/v1/embeddings")
async def embeddings(request: Request):
    data = await request.body()
    data = json.loads(data)

    try:
        res: Embedding = azure_client.embeddings.create(
            model=data["model"],
            input=data["input"],
        )

        return JSONResponse(content=jsonable_encoder(res))
    except Exception as e:
        try:
            log("Error occurred: ", e.__dict__)
            error_code = e.status_code
            error_message = e.message
        except:
            error_code = 500
            error_message = str(e)
        raise HTTPException(status_code=error_code, detail=f"Error occurred: {error_message}")

async def convert_stream(stream: Stream[ChatCompletionChunk]) -> AsyncIterable[str]:
    for chunk in stream:
        log("CHUNK: ", chunk.model_dump_json())
        yield "data: " + str(chunk.model_dump_json()) + "\n\n"


if __name__ == "__main__":
    import uvicorn
    import asyncio

    try:
        uvicorn.run("main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")),
                    log_level="debug" if debug else "critical", access_log=debug)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass