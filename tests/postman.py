from sanic import Sanic
from sanic.exceptions import ServerError
from sanic.response import text, json, file

from amyrose.core.authentication import register, login, requires_authentication, \
    logout, request_verification
from amyrose.core.authorization import requires_permission, requires_role
from amyrose.core.captcha import request_captcha, captcha, requires_captcha
from amyrose.core.initializer import initialize_rose
from amyrose.core.middleware import xss_prevention, https_redirect
from amyrose.core.models import RoseError, CaptchaSession, Account, Role, Permission
from amyrose.core.utils import text_verification_code, email_verification_code
from amyrose.core.verification import verify_account

app = Sanic('AmyRose tests')


@app.middleware('response')
async def response_middleware(request, response):
    xss_prevention(request, response)


@app.post('/register')
@requires_captcha()
async def on_register(request):
    account, none = await register(request, False)
    response = text('Registration successful')
    return response


@app.post('/register/verification')
async def on_register(request):
    account, verification_session = await register(request)
    await email_verification_code(account.email, verification_session.code)
    response = text('Registration successful')
    verification_session.encode(response)
    return response


@app.get('/captcha/img')
async def on_captcha_img(request):
    img_path = await CaptchaSession().get_client_img(request)
    response = await file(img_path)
    return response


@app.get('/captcha')
async def on_request_captcha(request):
    captcha_session = await request_captcha(request)
    response = text('Captcha request successful!')
    captcha_session.encode(response)
    return response


@app.post('/register/captcha')
@requires_captcha()
async def on_register_captcha(request):
    account = await register(request)
    response = text('Registration successful')
    return response


@app.post('/resend')
async def resend_verification_request(request):
    account, verification_session = await request_verification(request)
    await text_verification_code(account.phone, verification_session.code)
    response = text('Resend request successful.')
    verification_session.encode(response)
    return response


@app.post('/login')
async def on_login(request):
    account, authentication_session = await login(request)
    response = text('Login successful')
    authentication_session.encode(response)
    return response


@app.post('/logout')
async def on_logout(request):
    await logout(request)
    response = text('Logout successful')
    return response


@app.post('/verify')
async def on_verify(request):
    account, verification_session = await verify_account(request)
    return text('Verification successful')


@app.get("/test")
@requires_authentication()
async def test(request):
    return text('Hello auth world!')


@app.post('/createadmin')
async def on_create_admin(request):
    client = await Account.get_client(request)
    await Role().create(parent_uid=client.uid, name='Admin')
    return text('Hello Admin!')


@app.post('/createadminperm')
async def on_create_admin_perm(request):
    client = await Account().get_client(request)
    await Permission().create(parent_uid=client.uid, wildcard='admin:update')
    return text('Hello Admin who can only update!')


@app.get('/testclient')
async def on_test_client(request):
    client = await Account().get_client(request)
    return text('Hello ' + client.username + '!')


@app.get('/testperm')
@requires_permission('admin:update')
async def on_test_perm(request):
    return text('Admin who can only update gained access!')


@app.get('/testjson')
async def on_test_json(request):
    client = await Account().get_client(request)
    return json(client.json(), 200)


@app.get('/testrole')
@requires_role('Admin')
async def on_test_role(request):
    return text('Admin gained access!')


@app.exception(RoseError)
async def on_rose_error_test(request, exception: ServerError):
    payload = {
        'error': str(exception),
        'status': exception.status_code
    }
    return json(payload, status=exception.status_code)


if __name__ == '__main__':
    initialize_rose(app)
    app.run(host='0.0.0.0', port=8000, debug=True)
