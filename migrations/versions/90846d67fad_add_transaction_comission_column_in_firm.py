"""add transaction_comission column in firm
Revision ID: 90846d67fadRevises: 4c372e265ed6Create Date: 2014-11-20 16:58:21.900000
"""
# revision identifiers, used by Alembic.
revision = '90846d67fad'down_revision = '4c372e265ed6'
from alembic import opimport sqlalchemy as sadef upgrade(engine_name):    eval("upgrade_%s" % engine_name)()def downgrade(engine_name):    eval("downgrade_%s" % engine_name)()def upgrade_term():    op.add_column('firm', sa.Column(        'transaction_comission', sa.Integer(), nullable=True))def downgrade_term():    op.drop_column('firm', 'transaction_comission')def upgrade_stack():    passdef downgrade_stack():    passdef upgrade_payment():    pass    def downgrade_payment():    passdef upgrade_mobispot():    passdef downgrade_mobispot():    pass