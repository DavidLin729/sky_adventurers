from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///family_rewards.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/avatars'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上傳檔案大小為 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 確保上傳目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return {'user': user}
    return {'user': None}

# 資料庫模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    points = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    adventurer_level = db.Column(db.String(20), default='木級冒險者')
    avatar_url = db.Column(db.String(200), default='images/default_avatar.png')

    @property
    def used_points(self):
        # 已通過的兌換申請總積分
        return sum([r.reward.points for r in self.reward_redeems if r.status == 'approved'])

    @property
    def unused_points(self):
        return self.points

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    points = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    level = db.Column(db.String(2), default='E')  # S, A, B, C, D, E
    is_group = db.Column(db.Boolean, default=False)
    task_type = db.Column(db.String(10), default='每日')  # 每日, 每周, 每月, 隨機, 公會指派

class UserTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    completed_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    user = db.relationship('User', backref='tasks')
    task = db.relationship('Task', backref='user_tasks')

class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    points = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class RewardRedeem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reward_id = db.Column(db.Integer, db.ForeignKey('reward.id'), nullable=False)
    redeemed_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    user = db.relationship('User', backref='reward_redeems')
    reward = db.relationship('Reward', backref='redeems')

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200), nullable=False)
    unlock_condition = db.Column(db.String(200), nullable=False)
    unlock_target = db.Column(db.Integer, default=1)  # 需要完成的任務次數
    extra_points = db.Column(db.Integer, default=60)
    task_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User', backref='user_badges')
    badge = db.relationship('Badge', backref='user_badges')

# 裝飾器：檢查是否為管理員
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('需要管理員權限', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# 初始化管理員帳號
def init_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print('管理員帳號已建立')
    return admin

# 定義任務等級與對應積分
TASK_LEVEL_POINTS = {
    'S': 100,
    'A': 50,
    'B': 10,
    'C': 5,
    'D': 3,
    'E': 1
}

# 路由
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    tasks = Task.query.filter_by(is_active=True).all()
    user_tasks = UserTask.query.filter_by(user_id=session['user_id']).order_by(UserTask.completed_at.desc()).all()
    
    return render_template('index.html', 
                         current_user=current_user,
                         tasks=tasks,
                         user_tasks=user_tasks,
                         total_points=current_user.points + current_user.used_points,
                         used_points=current_user.used_points,
                         unused_points=current_user.unused_points)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            flash('登入成功！', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        flash('使用者名稱或密碼錯誤', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('兩次輸入的密碼不一致', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('使用者名稱已存在', 'error')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        flash('註冊成功！請登入', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    task = Task.query.get_or_404(task_id)
    user_task = UserTask(
        user_id=session['user_id'],
        task_id=task_id,
        completed_at=datetime.now()
    )
    db.session.add(user_task)
    db.session.commit()
    flash('任務已完成，等待審核', 'success')
    return redirect(url_for('index'))

# 管理員路由
@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = {
        'total_users': User.query.count(),
        'pending_tasks': UserTask.query.filter_by(status='pending').count(),
        'today_completed': UserTask.query.filter(
            UserTask.completed_at >= datetime.now().date()
        ).count()
    }
    recent_activities = UserTask.query.order_by(UserTask.completed_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', stats=stats, recent_activities=recent_activities)

@app.route('/admin/tasks')
@admin_required
def admin_tasks():
    tasks = Task.query.all()
    return render_template('admin/tasks.html', tasks=tasks)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    pending_tasks = UserTask.query.filter_by(status='pending').order_by(UserTask.completed_at.desc()).all()
    return render_template('admin/reviews.html', pending_tasks=pending_tasks)

@app.route('/admin/task/<int:task_id>', methods=['GET'])
@admin_required
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'points': task.points,
        'is_active': task.is_active,
        'level': task.level,
        'is_group': task.is_group,
        'task_type': task.task_type
    })

@app.route('/admin/task/<int:task_id>', methods=['DELETE'])
@admin_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return '', 204

@app.route('/admin/task/add', methods=['POST'])
@admin_required
def admin_add_task():
    level = request.form.get('level', 'E')
    points = TASK_LEVEL_POINTS.get(level, 1)
    task = Task(
        title=request.form.get('title'),
        description=request.form.get('description'),
        points=points,
        is_active=True,
        level=level,
        is_group=request.form.get('is_group') == 'on',
        task_type=request.form.get('task_type', '每日')
    )
    db.session.add(task)
    db.session.commit()
    flash('任務已新增', 'success')
    return redirect(url_for('admin_tasks'))

@app.route('/admin/task/edit', methods=['POST'])
@admin_required
def admin_edit_task():
    task = Task.query.get_or_404(request.form.get('task_id'))
    task.title = request.form.get('title')
    task.description = request.form.get('description')
    task.level = request.form.get('level', 'E')
    task.points = TASK_LEVEL_POINTS.get(task.level, 1)
    task.is_active = 'is_active' in request.form
    task.is_group = request.form.get('is_group') == 'on'
    task.task_type = request.form.get('task_type', '每日')
    db.session.commit()
    flash('任務已更新', 'success')
    return redirect(url_for('admin_tasks'))

@app.route('/admin/user/<int:user_id>/toggle_admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session['user_id']:
        flash('不能修改自己的管理員權限', 'error')
        return redirect(url_for('admin_users'))
    user.is_admin = not user.is_admin
    db.session.commit()
    flash('使用者權限已更新', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/task/<int:user_task_id>/review', methods=['POST'])
@admin_required
def review_task(user_task_id):
    user_task = UserTask.query.get_or_404(user_task_id)
    action = request.form.get('action')
    
    if action == 'approve':
        user_task.status = 'approved'
        user_task.user.points += user_task.task.points
        if 'review_notifications' not in session:
            session['review_notifications'] = []
        session['review_notifications'].append(f"您的任務『{user_task.task.title}』已通過審核，獲得 {user_task.task.points} 分！")
        
        # 檢查並頒發徽章
        check_and_award_badges(user_task.user_id)
        
        flash('任務已通過', 'success')
    elif action == 'reject':
        user_task.status = 'rejected'
        if 'review_notifications' not in session:
            session['review_notifications'] = []
        session['review_notifications'].append(f"您的任務『{user_task.task.title}』未通過審核，請再接再厲！")
        flash('任務已拒絕', 'success')
    
    db.session.commit()
    return redirect(url_for('admin_reviews'))

# 使用者：積分兌換頁面
@app.route('/rewards')
def rewards():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    current_user = User.query.get(session['user_id'])
    rewards = Reward.query.filter_by(is_active=True).all()
    my_redeems = RewardRedeem.query.filter_by(user_id=current_user.id).order_by(RewardRedeem.redeemed_at.desc()).all()
    return render_template('rewards.html', current_user=current_user, rewards=rewards, my_redeems=my_redeems,
                           total_points=current_user.points + current_user.used_points,
                           used_points=current_user.used_points,
                           unused_points=current_user.unused_points)

# 使用者：申請兌換獎勵
@app.route('/redeem/<int:reward_id>', methods=['POST'])
def redeem_reward(reward_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    reward = Reward.query.get_or_404(reward_id)
    if user.points < reward.points:
        flash('積分不足，無法兌換', 'error')
        return redirect(url_for('rewards'))
    redeem = RewardRedeem(user_id=user.id, reward_id=reward.id)
    db.session.add(redeem)
    db.session.commit()
    flash('兌換申請已送出，請等待管理員審核', 'success')
    return redirect(url_for('rewards'))

# 管理員：獎勵管理頁面
@app.route('/admin/rewards')
@admin_required
def admin_rewards():
    rewards = Reward.query.all()
    return render_template('admin/rewards.html', rewards=rewards)

# 管理員：新增獎勵
@app.route('/admin/reward/add', methods=['POST'])
@admin_required
def admin_add_reward():
    reward = Reward(
        name=request.form.get('name'),
        description=request.form.get('description'),
        points=int(request.form.get('points')),
        is_active='is_active' in request.form
    )
    db.session.add(reward)
    db.session.commit()
    flash('獎勵已新增', 'success')
    return redirect(url_for('admin_rewards'))

# 管理員：編輯獎勵
@app.route('/admin/reward/edit', methods=['POST'])
@admin_required
def admin_edit_reward():
    reward = Reward.query.get_or_404(request.form.get('reward_id'))
    reward.name = request.form.get('name')
    reward.description = request.form.get('description')
    reward.points = int(request.form.get('points'))
    reward.is_active = 'is_active' in request.form
    db.session.commit()
    flash('獎勵已更新', 'success')
    return redirect(url_for('admin_rewards'))

# 管理員：刪除獎勵
@app.route('/admin/reward/<int:reward_id>/delete', methods=['POST'])
@admin_required
def admin_delete_reward(reward_id):
    reward = Reward.query.get_or_404(reward_id)
    db.session.delete(reward)
    db.session.commit()
    flash('獎勵已刪除', 'success')
    return redirect(url_for('admin_rewards'))

# 管理員：兌換申請審核頁面
@app.route('/admin/redeems')
@admin_required
def admin_redeems():
    redeems = RewardRedeem.query.order_by(RewardRedeem.redeemed_at.desc()).all()
    return render_template('admin/redeems.html', redeems=redeems)

# 管理員：審核兌換申請
@app.route('/admin/redeem/<int:redeem_id>/review', methods=['POST'])
@admin_required
def review_redeem(redeem_id):
    redeem = RewardRedeem.query.get_or_404(redeem_id)
    action = request.form.get('action')
    if action == 'approve':
        if redeem.user.points < redeem.reward.points:
            flash('使用者積分不足，無法通過兌換', 'error')
        else:
            redeem.status = 'approved'
            redeem.user.points -= redeem.reward.points
            flash('兌換申請已通過', 'success')
    elif action == 'reject':
        redeem.status = 'rejected'
        flash('兌換申請已拒絕', 'success')
    db.session.commit()
    return redirect(url_for('admin_redeems'))

@app.route('/admin/user/add', methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    adventurer_level = request.form.get('adventurer_level', '木級冒險者')
    if not username or not password:
        flash('請填寫完整資訊', 'error')
        return redirect(url_for('admin_users'))
    if User.query.filter_by(username=username).first():
        flash('冒險者名稱已存在', 'error')
        return redirect(url_for('admin_users'))
    user = User(username=username, password_hash=generate_password_hash(password), is_active=True, adventurer_level=adventurer_level)
    db.session.add(user)
    db.session.commit()
    flash('冒險者已新增', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    username = request.form.get('username')
    password = request.form.get('password')
    adventurer_level = request.form.get('adventurer_level', user.adventurer_level)
    if username:
        user.username = username
    if password:
        user.password_hash = generate_password_hash(password)
    user.adventurer_level = adventurer_level
    db.session.commit()
    flash('冒險者已更新', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session['user_id']:
        flash('不能刪除自己', 'error')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash('使用者已刪除', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/toggle_active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash('使用者狀態已更新', 'success')
    return redirect(url_for('admin_users'))

@app.route('/adventurer_level_info')
def adventurer_level_info():
    return render_template('adventurer_level_info.html')

@app.route('/user_task_records')
def user_task_records():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_tasks = UserTask.query.filter_by(user_id=session['user_id']).order_by(UserTask.completed_at.desc()).all()
    return render_template('user_task_records.html', user_tasks=user_tasks)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/adventurer_profile')
@login_required
def adventurer_profile():
    user_id = session['user_id']
    user = User.query.get(user_id)
    user_tasks = UserTask.query.filter_by(user_id=user_id).order_by(UserTask.completed_at.desc()).limit(10).all()
    
    # 取得使用者已獲得的徽章
    user_badges = UserBadge.query.filter_by(user_id=user_id).join(Badge).filter(Badge.is_active == True).all()
    
    LEVEL_NAME_TO_NUM = {
        '木級冒險者': 1,
        '鐵級冒險者': 2,
        '銅級冒險者': 3,
        '銀級冒險者': 4,
        '金級冒險者': 5,
        '白金級冒險者': 6,
        '黑鋼級冒險者': 7,
        '秘銀級冒險者': 8,
        '山鐵級冒險者': 9,
        '神金級冒險者': 10,
        '傳說級冒險者': 11
    }
    LEVEL_NAME_TO_POINTS = {
        '木級冒險者': 0,
        '鐵級冒險者': 100,
        '銅級冒險者': 200,
        '銀級冒險者': 300,
        '金級冒險者': 400,
        '白金級冒險者': 500,
        '黑鋼級冒險者': 600,
        '秘銀級冒險者': 700,
        '山鐵級冒險者': 800,
        '神金級冒險者': 900,
        '傳說級冒險者': 1000
    }
    total_points = user.points + user.used_points
    level_num = LEVEL_NAME_TO_NUM.get(user.adventurer_level, 1)
    level_names = list(LEVEL_NAME_TO_POINTS.keys())
    current_index = level_names.index(user.adventurer_level)
    if current_index + 1 < len(level_names):
        next_level_name = level_names[current_index + 1]
        next_level_points = LEVEL_NAME_TO_POINTS[next_level_name]
    else:
        next_level_points = LEVEL_NAME_TO_POINTS[user.adventurer_level]  # 已達最高級
    return render_template('adventurer_profile.html', user=user, user_tasks=user_tasks, user_badges=user_badges, level_num=level_num, next_level_points=next_level_points, total_points=total_points)

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('沒有選擇檔案', 'error')
        return redirect(url_for('adventurer_profile'))
    
    file = request.files['avatar']
    if file.filename == '':
        flash('沒有選擇檔案', 'error')
        return redirect(url_for('adventurer_profile'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # 更新使用者的頭像 URL
        user = User.query.get(session['user_id'])
        user.avatar_url = f"uploads/avatars/{filename}"
        db.session.commit()
        
        flash('頭像已更新', 'success')
    else:
        flash('不支援的檔案格式', 'error')
    
    return redirect(url_for('adventurer_profile'))

@app.route('/badges')
def badges():
    badges = Badge.query.filter_by(is_active=True).order_by(Badge.created_at.asc()).all()
    return render_template('badges.html', badges=badges)

# 管理員：成就徽章管理頁面
@app.route('/admin/badges')
@admin_required
def admin_badges():
    badges = Badge.query.order_by(Badge.created_at.desc()).all()
    return render_template('admin/badges.html', badges=badges)

# 管理員：新增徽章
@app.route('/admin/badge/add', methods=['POST'])
@admin_required
def admin_add_badge():
    if 'image' not in request.files:
        flash('請選擇徽章圖檔', 'error')
        return redirect(url_for('admin_badges'))
    
    file = request.files['image']
    if file.filename == '':
        flash('請選擇徽章圖檔', 'error')
        return redirect(url_for('admin_badges'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"badge_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        file_path = os.path.join('static/images/badges', filename)
        
        # 確保目錄存在
        os.makedirs('static/images/badges', exist_ok=True)
        
        file.save(file_path)
        
        badge = Badge(
            name=request.form.get('name'),
            description=request.form.get('description'),
            image_url=f"images/badges/{filename}",
            unlock_condition=request.form.get('unlock_condition'),
            unlock_target=int(request.form.get('unlock_target', 1)),
            extra_points=int(request.form.get('extra_points', 60)),
            task_name=request.form.get('task_name'),
            is_active='is_active' in request.form
        )
        db.session.add(badge)
        db.session.commit()
        flash('徽章已新增', 'success')
    else:
        flash('不支援的檔案格式', 'error')
    
    return redirect(url_for('admin_badges'))

# 管理員：編輯徽章
@app.route('/admin/badge/edit', methods=['POST'])
@admin_required
def admin_edit_badge():
    badge = Badge.query.get_or_404(request.form.get('badge_id'))
    badge.name = request.form.get('name')
    badge.description = request.form.get('description')
    badge.unlock_condition = request.form.get('unlock_condition')
    badge.unlock_target = int(request.form.get('unlock_target', 1))
    badge.extra_points = int(request.form.get('extra_points', 60))
    badge.task_name = request.form.get('task_name')
    badge.is_active = 'is_active' in request.form
    
    # 處理圖檔更新
    if 'image' in request.files and request.files['image'].filename != '':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"badge_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file_path = os.path.join('static/images/badges', filename)
            
            # 確保目錄存在
            os.makedirs('static/images/badges', exist_ok=True)
            
            file.save(file_path)
            badge.image_url = f"images/badges/{filename}"
    
    db.session.commit()
    flash('徽章已更新', 'success')
    return redirect(url_for('admin_badges'))

# 管理員：刪除徽章
@app.route('/admin/badge/<int:badge_id>/delete', methods=['POST'])
@admin_required
def admin_delete_badge(badge_id):
    badge = Badge.query.get_or_404(badge_id)
    db.session.delete(badge)
    db.session.commit()
    flash('徽章已刪除', 'success')
    return redirect(url_for('admin_badges'))

def check_and_award_badges(user_id):
    """檢查並頒發徽章"""
    user = User.query.get(user_id)
    if not user:
        return
    
    # 取得所有啟用的徽章
    badges = Badge.query.filter_by(is_active=True).all()
    
    for badge in badges:
        if not badge.task_name:
            continue
            
        # 檢查使用者是否已經獲得此徽章
        existing_badge = UserBadge.query.filter_by(user_id=user_id, badge_id=badge.id).first()
        if existing_badge:
            continue
            
        # 計算使用者完成該任務的次數
        task_completion_count = UserTask.query.filter_by(
            user_id=user_id,
            status='approved'
        ).join(Task).filter(Task.title == badge.task_name).count()
        
        # 檢查是否達到解鎖目標
        if task_completion_count >= badge.unlock_target:
            # 頒發徽章
            user_badge = UserBadge(user_id=user_id, badge_id=badge.id)
            db.session.add(user_badge)
            
            # 給予額外積分
            user.points += badge.extra_points
            
            db.session.commit()
            
            # 設定通知
            if 'badge_notifications' not in session:
                session['badge_notifications'] = []
            session['badge_notifications'].append(f"恭喜獲得成就徽章『{badge.name}』！獲得 {badge.extra_points} 積分獎勵！")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_admin()  # 初始化管理員帳號
    app.run(host='0.0.0.0', port=5000, debug=True) 