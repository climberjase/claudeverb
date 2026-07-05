# Fable Deep Research: Physically Parameterized Room Models

**Date:** 2026-07-05

> A40 scattering delay networks (SDN) & room acoustic rendering networks · A41 digital waveguide networks & 3-D meshes. See also A11 (Gardner rooms) in the allpass-loop file.
> 
> Extracted from `Fable_research_detail.md` — the A-numbering, appendices (comparison tables, license summary, caveats) and the top-20 ranking (`fable_summary.md`) live there.

## A40. Scattering Delay Networks (SDN) + Room Acoustic Rendering Networks


**Paper:** De Sena, Hacıhabiboğlu, Cvetković, Smith, "Efficient Synthesis of Room Acoustics via Scattering Delay Networks," IEEE/ACM TASLP 23(9):1478–1492, 2015 — https://arxiv.org/abs/1502.05751; MATLAB reference: https://github.com/enzodesena/sdn-matlab; JOS chapter: https://ccrma.stanford.edu/~jos/lumped/Scattering_Delay_Networks.html

**Topology:** one scattering node per wall (cuboid → 6 nodes), placed at the first-order reflection point for the current source/listener geometry; every node pair joined by a bidirectional delay line; source/mic connect via unidirectional lines (+direct path):

```
            S (source)
          / | \  (1/d_Sk gains, delay d_Sk·fs/c)
        N1──N2          node scattering: S = (2/(N−1))·11ᵀ − I,  wall filter H_i(z)
        │╲ ╱│
        │ ╳ │           bidirectional lines, length d_ij·fs/c
        N3──N4 … N6
          \ | /  (output gains, delay d_kM·fs/c)
            M (mic)   + direct path S→M, gain 1/d_SM
```

**Math:** the isotropic scattering matrix `S = (2/(N−1))·11ᵀ − I` is a Householder-type reflection — orthogonal ⇒ lossless — and rank-1-plus-identity: apply as `p⁺_j = 2·mean(p⁻) − p⁻_j` (one mean + K adds, no matrix multiply). Wall absorption = scalar β_i = √(1−α_i) or wall filter H_i(z). Delays are physical propagation times; branch gains enforce the 1/r law so **first-order reflections are rendered exactly in time, amplitude and direction**; higher orders are progressively approximate but energy statistics match Sabine/Eyring.

**Extensions:** RARN (Scerbo, Savioja, De Sena, TASLP 2024 — https://arxiv.org/abs/2312.14658): surface patches instead of one node per wall, stability-preserving scattering, arbitrary numbers of exact early reflections — a tunable dial between cost and accuracy; differentiable SDN (DAFx-25 — https://www.dafx.de/paper-archive/2025/DAFx25_paper_51.pdf).

**Character:** the only delay-network reverb whose early field *moves correctly* when source/listener move — the physically-parameterized room/chamber option (a genuinely different "room" algorithm than Moorer-style tapped ERs).

## A41. Digital waveguide networks (DWN) & 3-D meshes


**Papers:** Smith & Rocchesso, "Connections between Feedback Delay Networks and Waveguide Networks for Digital Reverberation," ICMC 1994 — https://quod.lib.umich.edu/i/icmc/bbp2372.1994.098; Van Duyne & Smith, "The 2-D Digital Waveguide Mesh," ICMC 1993 — https://ccrma.stanford.edu/~jos/pdf/mesh.pdf; JOS PASP book — https://ccrma.stanford.edu/~jos/pasp/

**Lossless junction:** N waveguides with admittances Γ_i:

```
p_J  = ( 2·Σ_i Γ_i p_i⁺ ) / ( Σ_i Γ_i );      p_i⁻ = p_J − p_i⁺
```

**Key theoretical result:** an FDN with a Householder matrix **is exactly a single N-branch equal-impedance scattering junction**; multi-junction DWNs generate a much larger class of lossless FDN topologies (arbitrary graphs of unequal-impedance waveguides, lossless by construction). 2-D/3-D rectilinear meshes coincide with FDTD of the wave equation; dispersion error is direction-dependent (remedies: triangular/tetrahedral meshes, frequency warping); 3-D cost O(V·fs³/c³) → practical use is LF-only room modes + hybridization. **Use here:** the theory quarry for inventing new lossless topologies (it is where ring, FDN, and SDN meet), not a production reverb.
