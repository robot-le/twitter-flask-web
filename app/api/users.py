from app.api import bp


@bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    pass


@bp.route('/users', methods=['GET'])
def get_users():
    pass


@bp.route('/users/<int:user_id>/followers', methods=['GET'])
def get_followers(user_id):
    pass


@bp.route('/users/<int:user_id>/following', methods=['GET'])
def get_following(user_id):
    pass


@bp.route('/users', methods=['POST'])
def create_user():
    pass


@bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    pass
