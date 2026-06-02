from dotenv import load_dotenv
import os
import torch
from flask import Flask, render_template, send_from_directory
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
from wtforms import FileField, SubmitField, FloatField
from wtforms.validators import InputRequired
from PIL import Image
from torchvision import transforms
from flask import (
    render_template,
    request,
    redirect,
    url_for
)
# AdaIN imports
from utils.models import VGGEncoder, Decoder
from utils.utils import adaptive_instance_normalization
from database import db, User, Generation

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
load_dotenv()
# =========================================================
# Flask App Config
# =========================================================

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

app.config['SECRET_KEY'] = 'neuralbrush_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///neuralbrush.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))
Bootstrap(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# =========================================================
# Form
# =========================================================

class UploadForm(FlaskForm):

    content = FileField(
        'Content Image',
        validators=[InputRequired()]
    )

    style = FileField(
        'Style Image',
        validators=[InputRequired()]
    )

    alpha = FloatField(
        'Style Strength',
        default=1.0
    )

    submit = SubmitField('Generate Stylized Image')


# =========================================================
# Device Setup
# =========================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Using Device:", device)


# =========================================================
# Load Models
# =========================================================

VGG_PATH = 'vgg_normalised.pth'
DECODER_PATH = 'decoder_final.pth'

encoder = VGGEncoder(VGG_PATH).to(device)
decoder = Decoder().to(device)

state_dict = torch.load(
    DECODER_PATH,
    map_location=device
)

new_state_dict = {}

for k, v in state_dict.items():
    new_key = "net." + k
    new_state_dict[new_key] = v

decoder.load_state_dict(new_state_dict)

encoder.eval()
decoder.eval()


# =========================================================
# Helper Functions
# =========================================================

def allowed_file(filename):

    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower()
        in app.config['ALLOWED_EXTENSIONS']
    )


def preprocess_image(image):

    transform = transforms.Compose([
        transforms.Resize((768, 768)),
        transforms.ToTensor()
    ])

    image = transform(image).unsqueeze(0)

    return image.to(device)


def tensor_to_image(tensor):

    tensor = tensor.cpu().clone()

    tensor = tensor.squeeze(0)

    tensor = tensor.clamp(0, 1)

    image = transforms.ToPILImage()(tensor)

    return image


# =========================================================
# Style Transfer Function
# =========================================================

def style_transfer(content_image, style_image, alpha=1.0):

    content_tensor = preprocess_image(content_image)

    style_tensor = preprocess_image(style_image)

    with torch.no_grad():

        content_features = encoder(
            content_tensor,
            is_test=True
        )

        style_features = encoder(
            style_tensor,
            is_test=True
        )

        stylized_features = adaptive_instance_normalization(
            content_features,
            style_features
        )

        stylized_features = (
            alpha * stylized_features
            + (1 - alpha) * content_features
        )

        output = decoder(stylized_features)
        output = torch.clamp(
        output,
        0,
        1
)

    return output


# =========================================================
# Routes
# =========================================================

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = UploadForm()
    result_image = None
    error = None

    if form.validate_on_submit():
        content_file = form.content.data
        style_file = form.style.data

        if (content_file and allowed_file(content_file.filename)) and \
           (style_file and allowed_file(style_file.filename)):

            try:
                content_filename = secure_filename(content_file.filename)
                style_filename = secure_filename(style_file.filename)

                content_path = os.path.join(app.config['UPLOAD_FOLDER'], content_filename)
                style_path = os.path.join(app.config['UPLOAD_FOLDER'], style_filename)

                # ✅ FIX 1: Check file size BEFORE saving, and check both files
                if content_file.content_length > 10 * 1024 * 1024 or \
                   style_file.content_length > 10 * 1024 * 1024:
                    raise ValueError("File too large")

                # ✅ FIX 2: Save BOTH files (content_file.save was missing)
                content_file.save(content_path)
                style_file.save(style_path)

                # ✅ FIX 3: Open content image from saved path, not before saving
                try:
                    content_image = Image.open(content_path).convert('RGB')
                except Exception:
                    raise ValueError("Invalid content image")

                try:
                    style_image = Image.open(style_path).convert('RGB')
                except Exception:
                    raise ValueError("Invalid style image")

                alpha = float(form.alpha.data)
                alpha = max(0.0, min(alpha, 1.5))

                output_tensor = style_transfer(content_image, style_image, alpha)

                result_filename = 'stylized_' + content_filename
                result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)

                output_image = tensor_to_image(output_tensor)
                output_image.save(result_path)

                #  FIX 4: Moved inside try block with correct indentation
                if current_user.is_authenticated:
                    generation = Generation(
                        user_id=current_user.id,
                        content_image=content_filename,
                        style_image=style_filename,
                        output_image=result_filename,
                        alpha=alpha
                    )
                    db.session.add(generation)
                    db.session.commit()

                #  FIX 5: Moved inside try block so it's only set on success
                result_image = result_filename

            except Exception as e:
                error = str(e)

        else:
            error = "Invalid file type"

    return render_template('index.html', form=form, result_image=result_image, error=error)

# =========================================================
# Serve Uploaded Images
# =========================================================

@app.route('/uploads/<filename>')
def uploaded_file(filename):

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )
@app.route('/examples/<path:filename>')
def send_example(filename):

    return send_from_directory(
        'examples',
        filename
    )
@app.route('/images/<path:filename>')
def send_image(filename):

    return send_from_directory(
        'static/uploads',
        filename
    )
print(torch.cuda.is_available())

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']

        email = request.form['email']

        password = request.form['password']

        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(user)

        db.session.commit()

        return redirect('/login')

    return render_template('register.html')

#login route
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            next_page = request.args.get('next')

            return redirect(
                next_page or url_for('index')
            )

        else:
            return render_template(
                'login.html',
                error='Invalid Email or Password'
            )

    return render_template('login.html')
@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(url_for('login'))

@app.route('/gallery')
@login_required
def gallery():

    generations = Generation.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Generation.created_at.desc()
    ).all()

    return render_template(
        'gallery.html',
        generations=generations
    )
@app.route('/features')
def features():

    return render_template(
        'features.html'
    )
@app.route('/pricing')
def pricing():

    return render_template(
        'pricing.html'
    )
@app.route('/delete_image/<int:image_id>')
@login_required
def delete_image(image_id):

    image = Generation.query.get_or_404(image_id)

    if image.user_id != current_user.id:
        return redirect(url_for('gallery'))

    db.session.delete(image)

    db.session.commit()

    return redirect(url_for('gallery'))
with app.app_context():

    db.create_all()
# =========================================================
# Run App
# =========================================================

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )