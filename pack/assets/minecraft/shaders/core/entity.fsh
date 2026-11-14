#version 330
#extension GL_ARB_separate_shader_objects : require

#ifdef GLINT
#include <minecraft:globals.glsl>
#endif
#include <minecraft:fog.glsl>
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:oit.glsl>

uniform sampler2D Sampler0;

#ifdef DISSOLVE
uniform sampler2D DissolveMaskSampler;
#endif

#ifdef GLINT
uniform sampler2D GlintSampler;
#endif

layout(location = 0) in float sphericalVertexDistance;
layout(location = 1) in float cylindricalVertexDistance;
#ifdef PER_FACE_LIGHTING
layout(location = 2) in vec4 vertexPerFaceColorBack;
layout(location = 3) in vec4 vertexPerFaceColorFront;
#else
layout(location = 2) in vec4 vertexColor;
#endif

#ifndef EMISSIVE
layout(location = 4) in vec4 lightMapColor;
#endif

#ifndef NO_OVERLAY
layout(location = 5) in vec4 overlayColor;
#endif

layout(location = 6) in vec2 texCoord0;
#ifdef GLINT
layout(location = 7) in vec2 texCoordGlint;
#endif

#ifndef OIT_ALPHA_ONLY
layout(location = 0) out vec4 fragColor;
#endif

// Rally driver model: see entity.vsh. rallyNet is the position in the head's
// texture net (pixels of the 64 x 64 skin), rallyPart the part id.
layout(location = 8) in vec2 rallyNet;
layout(location = 9) flat in int rallyPart;

// Maps a point of the 8 x 8 x 8 head net (x 0..32, y 0..16; x 32..64 is the
// hat layer) onto the net of box (w, h, d) whose layers start at base / over.
vec2 rally_net(vec2 net, vec3 box, vec2 base, vec2 over) {
    bool outer = net.x >= 32.0;
    float x = outer ? net.x - 32.0 : net.x;
    float y = net.y;
    float w = box.x;
    float h = box.y;
    float d = box.z;
    float tx;
    float ty;
    if (y < 8.0) {
        // top face (x 8..16) and bottom face (x 16..24): w x d
        ty = y / 8.0 * d;
        tx = x < 16.0 ? d + (x - 8.0) / 8.0 * w : d + w + (x - 16.0) / 8.0 * w;
    } else {
        // right, front, left, back: d, w, d, w wide, h tall
        ty = d + (y - 8.0) / 8.0 * h;
        if (x < 8.0) {
            tx = x / 8.0 * d;
        } else if (x < 16.0) {
            tx = d + (x - 8.0) / 8.0 * w;
        } else if (x < 24.0) {
            tx = d + w + (x - 16.0) / 8.0 * d;
        } else {
            tx = d + w + d + (x - 24.0) / 8.0 * w;
        }
    }
    return ((outer ? over : base) + vec2(tx, ty)) / 64.0;
}

vec2 rally_uv(vec2 fallback) {
    switch (rallyPart) {
        case 2: return rally_net(rallyNet, vec3(8.0, 12.0, 4.0), vec2(16.0, 16.0), vec2(16.0, 32.0));
        case 3: return rally_net(rallyNet, vec3(4.0, 12.0, 4.0), vec2(40.0, 16.0), vec2(40.0, 32.0));
        case 4: return rally_net(rallyNet, vec3(4.0, 12.0, 4.0), vec2(32.0, 48.0), vec2(48.0, 48.0));
        case 5: return rally_net(rallyNet, vec3(4.0, 12.0, 4.0), vec2(0.0, 16.0), vec2(0.0, 32.0));
        case 6: return rally_net(rallyNet, vec3(4.0, 12.0, 4.0), vec2(16.0, 48.0), vec2(0.0, 48.0));
        case 7: return rally_net(rallyNet, vec3(3.0, 12.0, 4.0), vec2(40.0, 16.0), vec2(40.0, 32.0));
        case 8: return rally_net(rallyNet, vec3(3.0, 12.0, 4.0), vec2(32.0, 48.0), vec2(48.0, 48.0));
        default: return fallback;
    }
}

vec4 calculateFinalColor(vec4 color) {
    #ifndef NO_OVERLAY
    color.rgb = mix(overlayColor.rgb, color.rgb, overlayColor.a);
    #endif

    #ifndef EMISSIVE
    color *= lightMapColor;
    #endif

    #ifdef GLINT
    vec4 glintColor = GlintAlpha * texture(GlintSampler, texCoordGlint);
    // Matches BlendFuntion.GLINT
    color.rgb += glintColor.rgb * glintColor.rgb;
    #endif

    #ifdef OIT_ACCUMULATE
    color = sampleColorForAccumulation(color);
    vec4 fogColor = vec4(FogColor.rgb * color.a, FogColor.a);
    #else
    vec4 fogColor = FogColor;
    #endif

    return apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, fogColor);
}

void main() {
    vec4 color = texture(Sampler0, rally_uv(texCoord0));

    #ifdef OIT_ADDITIVE
    color.a = min(0.99, color.a);
    #endif

    #ifdef ALPHA_CUTOUT
    if (color.a < ALPHA_CUTOUT) {
        discard;
    }
    #endif

    #ifdef PER_FACE_LIGHTING
    vec4 faceVertexColor = gl_FrontFacing ? vertexPerFaceColorFront : vertexPerFaceColorBack;
    #else
    vec4 faceVertexColor = vertexColor;
    #endif

    #ifdef DISSOLVE
    if (faceVertexColor.a < texture(DissolveMaskSampler, texCoord0).a) {
        discard;
    }
    // The dissolve effect entirely replaces translucency
    faceVertexColor.a = 1.0;
    #endif

    color *= faceVertexColor * ColorModulator;

    #ifdef GLINT
    color.a = max(color.a, GlintAlpha);
    #endif

    #ifdef OIT_ALPHA_ONLY
    executeAlphaOnlyPhase(gl_FragCoord.z, color.a);
    #else
    fragColor = calculateFinalColor(color);
    #endif
}
