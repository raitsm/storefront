"""vendor name fix SalesItems 2

Revision ID: 6040a90c24ab
Revises: 364ba146b23e
Create Date: 2023-12-20 17:15:16.351192

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6040a90c24ab'
down_revision = '364ba146b23e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('sales_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vendor_name', sa.String(length=128), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('sales_items', schema=None) as batch_op:
        batch_op.drop_column('vendor_name')

    # ### end Alembic commands ###
