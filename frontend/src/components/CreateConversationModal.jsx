import { useState } from 'react';
import { createConversation } from '../api';

export default function CreateConversationModal({ onClose, onCreate }) {
  const [title, setTitle] = useState('');
  const [type, setType] = useState('group');
  const [memberIds, setMemberIds] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const ids = memberIds
        .split(',')
        .map((id) => parseInt(id.trim(), 10))
        .filter((id) => !isNaN(id));

      const conv = await createConversation(
        title || null,
        type,
        ids
      );
      onCreate(conv);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>New Conversation</h3>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="conv-title">Title (optional)</label>
            <input
              id="conv-title"
              type="text"
              placeholder="e.g. Project Discussion"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={100}
            />
          </div>

          <div className="form-group">
            <label htmlFor="conv-type">Type</label>
            <select
              id="conv-type"
              value={type}
              onChange={(e) => setType(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: '14px',
                fontFamily: "'Inter', sans-serif",
                outline: 'none',
              }}
            >
              <option value="group">Group</option>
              <option value="dm">Direct Message</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="conv-members">Member IDs (comma-separated)</label>
            <input
              id="conv-members"
              type="text"
              placeholder="e.g. 2, 3, 4"
              value={memberIds}
              onChange={(e) => setMemberIds(e.target.value)}
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" style={{ width: 'auto' }} disabled={loading}>
              {loading ? <span className="spinner" /> : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
