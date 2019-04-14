import json
import asyncio
from aiohttp import web
import aioredis
import uvloop
import aio_pika


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


async def count_handler(request):
    counter = await request.app['redis'].execute('incr', 'counter')
    return web.Response(text=f"{counter}")


async def count_and_publish_handler(request):
    counter = await request.app['redis'].execute('incr', 'counter')

    channel = await request.app['rabbitmq'].channel()
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps({"counter": counter}).encode(),
            delivery_mode=1
        ),
        routing_key="test"
    )
    await channel.close()

    return web.Response(text=f"{counter}")


async def redirect(request):
    return web.HTTPFound('https://ya.ru')


async def init_app(loop):
    app = web.Application()
    app['redis'] = await aioredis.create_connection('redis://redis', loop=loop)
    app['rabbitmq'] = await aio_pika.connect(
        "amqp://guest:guest@rabbitmq/",
        loop=loop
    )
    # Creating channel
    channel = await app['rabbitmq'].channel()
    # Declaring queue
    queue = await channel.declare_queue("test", auto_delete=False)
    # print(queue)
    await channel.close()

    return app


loop = asyncio.get_event_loop()
app = loop.run_until_complete(init_app(loop))

app.add_routes([
    web.get('/', count_handler),
    web.get('/count-and-publish', count_and_publish_handler),
    web.get('/r', redirect),
])

web.run_app(app, port=80)
