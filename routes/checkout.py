from flask import Blueprint, render_template

checkout_bp = Blueprint('checkout', __name__)

@checkout_bp.route('/checkout')
def checkout():
    return render_template('checkout.html')