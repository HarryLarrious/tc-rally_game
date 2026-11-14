#version 330
#extension GL_ARB_separate_shader_objects : require

#if defined(PER_FACE_LIGHTING) || !defined(NO_CARDINAL_LIGHTING)
#include <minecraft:light.glsl>
#endif
#include <minecraft:fog.glsl>
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:projection.glsl>
#include <minecraft:sample_lightmap.glsl>

layout(location = 0) in vec3 Position;
layout(location = 1) in vec4 Color;
layout(location = 2) in vec2 UV0;
layout(location = 3) in ivec2 UV1;
layout(location = 4) in ivec2 UV2;
layout(location = 5) in vec3 Normal;

#if !defined(NO_OVERLAY) && !defined(OIT_ALPHA_ONLY)
uniform sampler2D Sampler1;
#endif

#if !defined(EMISSIVE) && !defined(OIT_ALPHA_ONLY)
uniform sampler2D Sampler2;
#endif

layout(location = 0) out float sphericalVertexDistance;
layout(location = 1) out float cylindricalVertexDistance;

#ifdef PER_FACE_LIGHTING
layout(location = 2) out vec4 vertexPerFaceColorBack;
layout(location = 3) out vec4 vertexPerFaceColorFront;
#else
layout(location = 2) out vec4 vertexColor;
#endif

#ifndef EMISSIVE
layout(location = 4) out vec4 lightMapColor;
#endif

#ifndef NO_OVERLAY
layout(location = 5) out vec4 overlayColor;
#endif

layout(location = 6) out vec2 texCoord0;
#ifdef GLINT
layout(location = 7) out vec2 texCoordGlint;
#endif

// Rally driver model (tc-rally_game): player heads on item displays drawn as
// the other body parts. A display marks its part with its brightness
// override: sky light 0, block light = part id 1..8 (head, torso, right arm,
// left arm, right leg, left leg, slim right arm, slim left arm). The fragment
// shader maps the head's texture net onto that part's net.
layout(location = 8) out vec2 rallyNet;
layout(location = 9) flat out int rallyPart;

int rally_part() {
    if (UV2.y != 0 || UV2.x < 16 || UV2.x > 128 || (UV2.x & 15) != 0) {
        return 0;
    }
    // Only head geometry: its net is the top 16 rows of the 64 x 64 skin.
    if (UV0.y > 0.2502) {
        return 0;
    }
    return UV2.x >> 4;
}

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    int part = rally_part();
    rallyPart = part;
    rallyNet = UV0 * 64.0;
    // The driver's own head would fill their first-person view: drop it when
    // the camera is inside it (Position is relative to the camera).
    if (part == 1 && length(Position) < 0.9) {
        gl_Position = vec4(0.0, 0.0, -2.0, 1.0);
    }

    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);

#ifdef PER_FACE_LIGHTING
    vec2 light = minecraft_compute_light(Light0_Direction, Light1_Direction, Normal);
    vertexPerFaceColorBack = minecraft_mix_light_separate(-light, Color);
    vertexPerFaceColorFront = minecraft_mix_light_separate(light, Color);
#elif defined(NO_CARDINAL_LIGHTING)
    vertexColor = Color;
#else
    vertexColor = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color);
#endif

#if !defined(EMISSIVE) && !defined(OIT_ALPHA_ONLY)
    // Marked parts are lit like the car's displays (full bright).
    lightMapColor = sample_lightmap(Sampler2, part > 0 ? ivec2(240, 240) : UV2);
#endif

#if !defined(NO_OVERLAY) && !defined(OIT_ALPHA_ONLY)
    overlayColor = texelFetch(Sampler1, UV1, 0);
#endif

    texCoord0 = UV0;

#ifdef APPLY_TEXTURE_MATRIX
    texCoord0 = (TextureMat * vec4(UV0, 0.0, 1.0)).xy;
#endif

#ifdef GLINT
    texCoordGlint = (TextureMat * vec4(UV0, 0.0, 1.0)).xy;
#endif
}
