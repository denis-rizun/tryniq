'use client';

import { useState } from 'react';
import { Avatar } from '@/components/ui/avatar';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import type { PeopleMap } from '@/lib/types';

const PARTICIPANTS = ['sarah', 'mike', 'anna'];

interface ExtensionPopupProps {
  people: PeopleMap;
}

export const ExtensionPopup = ({ people }: ExtensionPopupProps) => {
  const [recording, setRecording] = useState(true);
  return (
    <div
      style={{
        padding: '40px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 16,
      }}
    >
      <SectionLabel>EXTENSION POPUP</SectionLabel>
      <div className="mono" style={{ fontSize: 11, color: 'var(--color-ink-tertiary)' }}>
        360 × 420
      </div>
      <div className="ext-popup">
        <div
          style={{
            padding: '16px 16px 12px',
            borderBottom: '1px solid var(--color-border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span
              className="rec-dot"
              style={{
                background: recording ? 'var(--color-accent-500)' : 'var(--color-ink-tertiary)',
                animation: recording ? 'pulse-rec 1.6s ease-in-out infinite' : 'none',
              }}
            />
            <span style={{ fontSize: 13, fontWeight: 600 }}>
              {recording ? 'Recording' : 'Idle'}
            </span>
            <span
              className="mono"
              style={{ fontSize: 11, color: 'var(--color-ink-secondary)', marginLeft: 'auto' }}
            >
              {recording ? '14:23' : ''}
            </span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--color-ink-secondary)', marginTop: 4 }}>
            {recording ? 'Production deploy debrief' : 'Ready to capture'}
          </div>
        </div>

        <div style={{ padding: '12px 16px' }}>
          <button
            type="button"
            className={`btn ${recording ? '' : 'btn-primary'}`}
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={() => setRecording((r) => !r)}
          >
            {recording ? (
              <>
                <Icon name="square" size={12} /> Stop recording
              </>
            ) : (
              <>
                <Icon name="mic" size={12} color="var(--color-paper)" /> Start recording
              </>
            )}
          </button>
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--color-decision)',
              marginTop: 10,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <span className="status-dot" style={{ background: 'var(--color-decision)' }} />
            Connected to api
          </div>
        </div>

        <div
          style={{
            padding: '4px 16px 12px',
            borderTop: '1px solid var(--color-border-subtle)',
            flex: 1,
            overflow: 'hidden',
          }}
        >
          <div style={{ marginTop: 10 }}>
            <SectionLabel>PARTICIPANTS</SectionLabel>
          </div>
          {PARTICIPANTS.map((pid) => {
            const p = people[pid];
            const isActive = pid === 'mike' && recording;
            return (
              <div
                key={pid}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 6px',
                  borderLeft: isActive
                    ? '2px solid var(--color-accent-500)'
                    : '2px solid transparent',
                }}
              >
                <Avatar person={p} />
                <span style={{ fontSize: 13, flex: 1 }}>{p.name}</span>
                {isActive && (
                  <span style={{ fontSize: 11, color: 'var(--color-accent-500)' }}>speaking</span>
                )}
              </div>
            );
          })}
        </div>

        <div style={{ borderTop: '1px solid var(--color-border-subtle)', padding: '10px 16px' }}>
          <button
            type="button"
            style={{
              fontSize: 12,
              color: 'var(--color-accent-500)',
              cursor: 'pointer',
              background: 'none',
              border: 'none',
              padding: 0,
              font: 'inherit',
            }}
          >
            Open meeting view ↗
          </button>
        </div>
      </div>
    </div>
  );
};
