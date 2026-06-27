"""v0.4 cognitive domains and routing layer

Revision ID: a2b3c4d5e6f7
Revises: c1319c77c3cc
Create Date: 2026-06-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'c1319c77c3cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cognitive Domain table
    op.create_table('cognitive_domain',
        sa.Column('domain_id', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('routing_weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('decay_tier', sa.String(), nullable=False, server_default='medium'),
        sa.Column('nsi_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cbb_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('domain_id')
    )

    # Routing Session table
    op.create_table('routing_session',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(), nullable=False, server_default='explain'),
        sa.Column('nodes_considered', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('domains_considered', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('subdomains_considered', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('cbbs_discovered', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('beam_iterations', sa.Integer(), nullable=True),
        sa.Column('conflicts_detected', sa.Integer(), server_default='0'),
        sa.Column('selected_path_id', sa.String(), nullable=True),
        sa.Column('routing_confidence', sa.Float(), nullable=True),
        sa.Column('cache_hit', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('session_id')
    )

    # Conflict Artifact table
    op.create_table('conflict_artifact',
        sa.Column('conflict_id', sa.String(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(), nullable=True),
        sa.Column('path_id_a', sa.String(), nullable=False),
        sa.Column('path_id_b', sa.String(), nullable=False),
        sa.Column('conclusion_a', sa.Text(), nullable=True),
        sa.Column('conclusion_b', sa.Text(), nullable=True),
        sa.Column('conflict_type', sa.String(), nullable=True),
        sa.Column('resolution', sa.String(), server_default='unresolved'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('conflict_id')
    )

    # Path Feedback table
    op.create_table('path_feedback',
        sa.Column('feedback_id', sa.String(), nullable=False),
        sa.Column('path_id', sa.String(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('feedback_source', sa.String(), server_default='user'),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('feedback_id')
    )

    # Path Validation table
    op.create_table('path_validation',
        sa.Column('validation_id', sa.String(), nullable=False),
        sa.Column('path_id', sa.String(), nullable=False),
        sa.Column('sample_reason', sa.String(), nullable=True),
        sa.Column('coherence_passed', sa.Boolean(), nullable=True),
        sa.Column('coherence_break_step', sa.Integer(), nullable=True),
        sa.Column('coherence_reason', sa.Text(), nullable=True),
        sa.Column('path_optimal', sa.Boolean(), nullable=True),
        sa.Column('chosen_score', sa.Float(), nullable=True),
        sa.Column('best_alt_score', sa.Float(), nullable=True),
        sa.Column('optimality_gap', sa.Float(), nullable=True),
        sa.Column('action_taken', sa.String(), nullable=True),
        sa.Column('routing_adjustment', sa.JSON(), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('validation_id')
    )

    # Add columns to reasoning_path
    op.add_column('reasoning_path', sa.Column('path_utility', sa.Float(), server_default='0.5'))
    op.add_column('reasoning_path', sa.Column('path_relevance', sa.Float(), nullable=True))
    op.add_column('reasoning_path', sa.Column('path_rank_score', sa.Float(), nullable=True))
    op.add_column('reasoning_path', sa.Column('routing_confidence', sa.Float(), nullable=True))
    op.add_column('reasoning_path', sa.Column('intent', sa.String(), server_default='explain'))
    op.add_column('reasoning_path', sa.Column('cache_hit', sa.Boolean(), server_default='false'))

    # Add columns to nsi_cluster (if table exists)
    op.add_column('nsi_cluster', sa.Column('cognitive_domain', sa.String(), nullable=True))
    op.add_column('nsi_cluster', sa.Column('routing_weight', sa.Float(), server_default='1.0'))

    # Add CBB saturation tracking
    op.add_column('cbb', sa.Column('query_appearance_count', sa.Integer(), server_default='0'))
    op.add_column('cbb', sa.Column('saturation_score', sa.Float(), server_default='0.0'))


def downgrade() -> None:
    op.drop_column('cbb', 'saturation_score')
    op.drop_column('cbb', 'query_appearance_count')
    op.drop_column('nsi_cluster', 'routing_weight')
    op.drop_column('nsi_cluster', 'cognitive_domain')
    op.drop_column('reasoning_path', 'cache_hit')
    op.drop_column('reasoning_path', 'intent')
    op.drop_column('reasoning_path', 'routing_confidence')
    op.drop_column('reasoning_path', 'path_rank_score')
    op.drop_column('reasoning_path', 'path_relevance')
    op.drop_column('reasoning_path', 'path_utility')
    op.drop_table('path_validation')
    op.drop_table('path_feedback')
    op.drop_table('conflict_artifact')
    op.drop_table('routing_session')
    op.drop_table('cognitive_domain')