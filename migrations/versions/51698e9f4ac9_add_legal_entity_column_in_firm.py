"""add legal_entity column in firm
Revision ID: 51698e9f4ac9Revises: 4c29f0d0b393Create Date: 2014-11-27 10:44:59.733000
"""
# revision identifiers, used by Alembic.
revision = '51698e9f4ac9'down_revision = '4c29f0d0b393'
from alembic import opimport sqlalchemy as sadef upgrade(engine_name):    eval("upgrade_%s" % engine_name)()def downgrade(engine_name):    eval("downgrade_%s" % engine_name)()def upgrade_term():    op.add_column('firm', sa.Column(        'legal_entity', sa.String(256), nullable=True))def downgrade_term():    op.drop_column('firm', 'legal_entity')def upgrade_stack():    passdef downgrade_stack():    passdef upgrade_payment():    pass    def downgrade_payment():    passdef upgrade_mobispot():    passdef downgrade_mobispot():    pass