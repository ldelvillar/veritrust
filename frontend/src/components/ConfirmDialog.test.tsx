import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import ConfirmDialog from './ConfirmDialog';

const baseProps = {
  title: '¿Eliminar este análisis?',
  description: 'Esta acción no se puede deshacer.',
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
};

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    render(<ConfirmDialog open={false} {...baseProps} />);
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('renders title and description when open', () => {
    render(<ConfirmDialog open {...baseProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('¿Eliminar este análisis?')).toBeInTheDocument();
    expect(
      screen.getByText('Esta acción no se puede deshacer.')
    ).toBeInTheDocument();
  });

  it('calls onConfirm when the confirm button is clicked', async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog open {...baseProps} onConfirm={onConfirm} />);
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when the cancel button is clicked', async () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open {...baseProps} onCancel={onCancel} />);
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when Escape is pressed', async () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open {...baseProps} onCancel={onCancel} />);
    await userEvent.keyboard('{Escape}');
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('disables actions and shows the error message while confirming', () => {
    render(
      <ConfirmDialog
        open
        {...baseProps}
        isConfirming
        errorMessage="No se pudo eliminar el análisis."
      />
    );
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'No se pudo eliminar el análisis.'
    );
  });
});
