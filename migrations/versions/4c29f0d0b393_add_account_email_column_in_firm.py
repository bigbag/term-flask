"""add account_email column in firm
Revision ID: 4c29f0d0b393Revises: 132424e9f86bCreate Date: 2014-11-20 17:53:00.628000
"""
# revision identifiers, used by Alembic.
revision = '4c29f0d0b393'down_revision = '132424e9f86b'
from alembic import op
import sqlalchemy as sa
from alembic import opimport sqlalchemy as sadef upgrade(engine_name):    eval("upgrade_%s" % engine_name)()def downgrade(engine_name):    eval("downgrade_%s" % engine_name)()def upgrade_term():    op.add_column('firm', sa.Column(        'account_email', sa.Text(), nullable=True))def downgrade_term():    op.drop_column('firm', 'account_email')def upgrade_stack():    passdef downgrade_stack():    passdef upgrade_payment():    pass    def downgrade_payment():    passdef upgrade_mobispot():    passdef downgrade_mobispot():    pass