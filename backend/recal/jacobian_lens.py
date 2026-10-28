"""Full norm/head Jacobian-vector product, not the network's full Jacobian."""
def project_jacobian(norm, head_weight, anchor, states):
    import torch
    # Exact derivative of the final norm at a fit-only anchor. The head is
    # affine, so its bias derivative is zero; every vocabulary row is used.
    if anchor.ndim!=1 or states.ndim!=2 or states.shape[1]!=anchor.shape[0]:
        raise ValueError('Anchor/feature shapes disagree')
    if head_weight.ndim!=2 or head_weight.shape[1]!=anchor.shape[0]:
        raise ValueError('Unembedding shape mismatch')
    tangents=torch.stack([torch.func.jvp(norm,(anchor,),(row-anchor,))[1] for row in states])
    result=tangents @ head_weight.T
    if not torch.isfinite(result).all():raise ValueError('Nonfinite Jacobian projection')
    return result
