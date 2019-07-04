#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sanic import Sanic, Blueprint
from sanic.response import text

from sanic_limiter import Limiter, get_remote_address

from sanic import Sanic
from sanic.response import redirect
from sanic_jinja2 import SanicJinja2
from sanic_motor import BaseModel

app = Sanic(__name__)
limiter = Limiter(app, global_limits=['5 per minute'], key_func=get_remote_address)
bp = Blueprint('main')
limiter.limit("5 per minute")(bp)

settings = dict(MOTOR_URI='mongodb://localhost:27017/main',
                LOGO=None,
                )
app.config.update(settings)

BaseModel.init_app(app)
jinja = SanicJinja2(app, autoescape=True)

class User(BaseModel):
    __coll__ = 'users'
    __unique_fields__ = ['name']

@app.route("/")
# @bp.route("/")
@limiter.limit("5/minute")
async def index(request):
    cur = await User.find(sort='name, age desc')
    return jinja.render('index.html', request, users=cur.objects)

# @bp.route('/new', methods=('GET', 'POST'))
@app.route('/new', methods=('GET', 'POST'))
async def new(request):
    if request.method == 'POST':
        name = request.form.get('name', '').strip().lower()
        age = request.form.get('age', '').strip()
        if name:
            is_uniq = await User.is_unique(doc=dict(name=name))
            if is_uniq in (True, None):
                await User.insert_one(dict(name=name, age=int(age)))
                request['flash']('User was added successfully', 'success')
                return redirect(app.url_for('index'))
            else:
                request['flash']('This name was already taken', 'error')

        request['flash']('User name is required', 'error')

    return jinja.render('form.html', request, user={})


# @bp.route('/edit/<id>', methods=('GET', 'POST'))
@app.route('/edit/<id>', methods=('GET', 'POST'))
async def edit(request, id):
    user = await User.find_one(id)
    if not user:
        request['flash']('User not found', 'error')
        return redirect(app.url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip().lower()
        age = request.form.get('age', '').strip()
        if name:
            doc = dict(name=name, age=int(age))
            is_uniq = await User.is_unique(doc=doc, id=user.id)
            if is_uniq in (True, None):
                # remove non-changed items
                user.clean_for_dirty(doc)
                if doc:
                    await User.update_one({'_id': user.id}, {'$set': doc})

                request['flash']('User was updated successfully', 'success')
                return redirect(app.url_for('index'))
            else:
                request['flash']('This name was already taken', 'error')

        request['flash']('User name is required', 'error')

    return jinja.render('form.html', request, user=user)


# @bp.route('/destroy/<id>')
@app.route('/destroy/<id>')
async def destroy(request, id):
    user = await User.find_one(id)
    if not user:
        request['flash']('User not found', 'error')
        return redirect(app.url_for('index'))

    await user.destroy()
    request['flash']('User was deleted successfully', 'success')
    return redirect(app.url_for('index'))



app.blueprint(bp)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
#app.run(host="0.0.0.0", port=5000, debug=True)