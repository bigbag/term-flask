"""add transaction_percent column in firm
Revision ID: 4c372e265ed6Revises: 31c8c264892cCreate Date: 2014-11-20 16:56:32.756000
"""
# revision identifiers, used by Alembic.revision = '4c372e265ed6'down_revision = '31c8c264892c'
from alembic import opimport sqlalchemy as sa

def upgrade(engine_name):    eval("upgrade_%s" % engine_name)()

def downgrade(engine_name):    eval("downgrade_%s" % engine_name)()
def upgrade_term():    op.add_column('firm', sa.Column(        'transaction_percent', sa.Integer(), nullable=True))
def downgrade_term():    op.drop_column('firm', 'transaction_percent')
def upgrade_stack():    pass
def downgrade_stack():    pass
def upgrade_payment():    pass    
def downgrade_payment():    pass
def upgrade_mobispot():    pass
def downgrade_mobispot():    pass