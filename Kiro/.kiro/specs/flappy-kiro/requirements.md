# Requirements Document

## Introduction

Flappy Kiro is a retro browser-based endless scroller game inspired by Flappy Bird. The player controls a ghost character (Ghosty) that must navigate through an infinite series of green pipe obstacles by tapping/clicking to flap. The game features a sketchy hand-drawn visual style, sound effects, and a persistent high score. It runs entirely in the browser with no server-side dependencies.

## Glossary

- **Game**: The Flappy Kiro browser application
- **Ghosty**: The ghost sprite character controlled by the player
- **Pipe**: A green vertical obstacle pair (top and bottom) with a gap the player must pass through
- **Gap**: The vertical opening between the top and bottom pipe through which Ghosty must fly
- **Score**: The count of pipe pairs successfully passed during the current session
- **High_Score**: The highest Score achieved across all sessions, persisted in browser storage
- **Game_Loop**: The continuous update-and-render cycle that drives gameplay
- **Canvas**: The HTML5 canvas element on which the game is rendered
- **Gravity**: The constant downward acceleration (in pixels per frame²) applied to Ghosty's vertical velocity each frame
- **Flap**: The upward velocity impulse applied to Ghosty when the player inputs a tap or click
- **Flap_Velocity**: The fixed negative (upward) vertical velocity assigned to Ghosty on each Flap input
- **Terminal_Velocity**: The maximum downward vertical speed Ghosty may reach, beyond which Gravity no longer accelerates Ghosty
- **Vertical_Velocity**: Ghosty's current rate of vertical movement in pixels per frame, positive downward
- **Interpolation**: The technique of computing Ghosty's rendered position as a smooth blend between physics frames to eliminate jerky motion
- **Collision**: Contact between Ghosty's Hitbox and a Pipe bounding box or a Canvas boundary
- **Hitbox**: The axis-aligned rectangular region used for collision testing, inset from Ghosty's sprite bounds to produce fairer collision feel
- **Hitbox_Inset**: The number of pixels by which the Hitbox is shrunk on each side relative to the sprite's bounding box
- **Ground_Collision**: A Collision caused by Ghosty's Hitbox reaching or crossing the bottom boundary of the Canvas
- **Ceiling_Collision**: A Collision caused by Ghosty's Hitbox reaching or crossing the top boundary of the Canvas
- **Wall_Collision**: A Collision caused by Ghosty's Hitbox overlapping a Pipe bounding box
- **Collision_Animation**: A brief visual effect (flash or screen shake) played immediately after a Collision is detected, before the Game_Over_Screen is shown
- **Invincibility_Frame**: A fixed-duration window at the very start of each game session during which Ghosty cannot trigger a Collision, giving the player a brief grace period to establish control
- **Invincibility_Duration**: The length in milliseconds of the Invincibility_Frame window
- **Start_Screen**: The initial screen shown when the Game_State is MENU, before gameplay begins
- **Game_Over_Screen**: The screen shown when the Game_State is GAME_OVER, after a Collision occurs
- **Pause_Overlay**: A semi-transparent overlay rendered over the Canvas when the Game_State is PAUSED, indicating the game is paused
- **Score_Bar**: The UI strip at the bottom of the Canvas displaying Score and High_Score
- **Pipe_Speed**: The current horizontal scroll speed of all Pipes, measured in pixels per frame, which increases as the Score rises
- **Base_Pipe_Speed**: The initial Pipe_Speed value at the start of each game session, before any progressive increase
- **Speed_Increment**: The fixed amount added to Pipe_Speed each time the Score reaches a defined milestone, controlling how quickly the game accelerates
- **Pipe_Spacing**: The fixed horizontal distance in pixels between the left edge of one Pipe pair and the left edge of the next
- **Gap_Size**: The fixed vertical height in pixels of the opening between the top and bottom Pipe through which Ghosty must fly
- **Safe_Zone**: The vertical region of the Canvas within which the Gap centre may be randomly placed, ensuring the Gap is fully visible and not too close to the top or bottom edge
- **Game_State**: The discrete state the Game is currently in; one of MENU, PLAYING, PAUSED, or GAME_OVER. Only one Game_State is active at any time.
- **MENU**: The Game_State in which the Start_Screen is displayed and no active gameplay is occurring
- **PLAYING**: The Game_State in which the Game_Loop is running, Ghosty is subject to physics, and Pipes are scrolling
- **PAUSED**: The Game_State in which the Game_Loop is halted mid-session, the Pause_Overlay is shown, and no physics or pipe movement occurs; cloud animations continue
- **GAME_OVER**: The Game_State in which the Game_Loop has stopped following a Collision and the Game_Over_Screen is displayed
- **Background_Music**: A looping ambient or retro audio track that plays during the PLAYING state, loaded from a configurable asset path defined as a named constant
- **Particle**: A single short-lived visual element emitted from Ghosty's position, rendered as a small translucent shape that fades out over a defined duration
- **Particle_Trail**: The continuous stream of Particles emitted from Ghosty while the Game_State is PLAYING, producing a ghost-like or sparkle visual effect
- **Score_Popup**: A brief animated text element displaying "+1" that appears near the top of the Canvas each time the Score increments, floating upward and fading out over a short defined duration
- **Cloud**: A semi-transparent white shape rendered in the background to suggest sky depth
- **Cloud_Layer**: A group of Clouds that share the same horizontal scroll speed, used to create a parallax depth effect

## Requirements

### Requirement 1: Game Initialization and Main Menu

**User Story:** As a player, I want to see a start screen when I open the game that shows my high score prominently, so that I know how to begin playing and can see my best performance at a glance.

#### Acceptance Criteria

1. WHEN the browser loads the Game, THE Game SHALL set the Game_State to MENU and display the Start_Screen with the title "Flappy Kiro" and a prompt to press Space or tap to start.
2. WHILE the Game_State is MENU, THE Start_Screen SHALL display the High_Score prominently, labelled "Best", in a font size visually larger than the start prompt.
3. THE Game SHALL render all content on a single HTML5 Canvas element sized to fit the browser viewport.
4. WHILE the Game_State is MENU, THE Game SHALL show Ghosty in an idle floating animation.
5. WHEN the player presses Space or clicks/taps the Canvas while the Game_State is MENU, THE Game SHALL set the Game_State to PLAYING and begin active gameplay.

### Requirement 2: Ghosty Physics

**User Story:** As a player, I want Ghosty to move under a realistic physics system with gravity, flap impulse, terminal velocity, and smooth motion, so that the game has a satisfying and fluid feel.

#### Acceptance Criteria

1. WHILE the Game_State is PLAYING, THE Game_Loop SHALL add a defined Gravity constant (in pixels per frame²) to Ghosty's Vertical_Velocity once per frame, accumulating downward acceleration over time.
2. WHEN the player presses Space or clicks/taps the Canvas while the Game_State is PLAYING, THE Game SHALL set Ghosty's Vertical_Velocity to the defined Flap_Velocity (a fixed negative value), replacing the current Vertical_Velocity rather than adding to it.
3. WHILE the Game_State is PLAYING, THE Game_Loop SHALL update Ghosty's vertical position by adding the current Vertical_Velocity to the previous position each frame, preserving momentum between frames without abrupt resets.
4. WHILE the Game_State is PLAYING, THE Game_Loop SHALL clamp Ghosty's Vertical_Velocity to a defined Terminal_Velocity so that downward speed cannot exceed that value regardless of how long Ghosty falls.
5. WHILE the Game_State is PLAYING, THE Game_Loop SHALL compute Ghosty's rendered vertical position using Interpolation between the previous and current physics positions, so that motion appears smooth at any display refresh rate.
6. WHILE the Game_State is PLAYING, THE Game SHALL play the `assets/jump.wav` sound effect on each Flap.
7. WHILE the Game_State is PLAYING, THE Game_Loop SHALL clamp Ghosty's vertical position so that the top of Ghosty's sprite cannot move above the top edge of the Canvas.

### Requirement 3: Pipe Generation and Scrolling

**User Story:** As a player, I want an endless stream of pipe obstacles with well-defined spacing, gap sizing, and progressively increasing speed, so that the game provides a continuous and escalating challenge.

#### Acceptance Criteria

1. WHILE the Game_State is PLAYING, THE Game_Loop SHALL scroll all Pipes leftward by the current Pipe_Speed value each frame.
2. THE Game SHALL define Base_Pipe_Speed as a named constant representing the initial scroll speed at the start of each session.
3. WHEN the Game_State transitions to PLAYING at the start of a new session, THE Game SHALL set Pipe_Speed to Base_Pipe_Speed.
4. WHEN a Pipe pair exits the left edge of the Canvas, THE Game SHALL remove that Pipe pair and generate a new Pipe pair positioned at the right edge of the Canvas plus Pipe_Spacing pixels from the previous Pipe pair's spawn position.
5. THE Game SHALL define Pipe_Spacing as a named constant representing the fixed horizontal distance in pixels between consecutive Pipe pair spawn positions.
6. THE Game SHALL define Gap_Size as a named constant representing the fixed vertical height in pixels of the opening between the top and bottom Pipe.
7. WHEN a new Pipe pair is generated, THE Game SHALL set the Gap height to exactly Gap_Size pixels.
8. WHEN a new Pipe pair is generated, THE Game SHALL randomly select the vertical centre of the Gap from within the Safe_Zone, where the Safe_Zone ensures the Gap is fully visible and the Gap edge is no closer than a defined minimum margin to the top or bottom of the Canvas.
9. THE Game SHALL define Speed_Increment as a named constant representing the fixed amount added to Pipe_Speed each time the Score increases by a defined milestone interval.
10. WHEN the Score increases and the new Score value is a multiple of the defined milestone interval, THE Game SHALL increase Pipe_Speed by Speed_Increment.
11. THE Game SHALL define a maximum Pipe_Speed cap so that Pipe_Speed cannot increase beyond a value that makes the game unplayable.

### Requirement 4: Collision Detection

**User Story:** As a player, I want the game to detect collisions fairly and respond with clear visual feedback before ending, so that losses feel accurate and understandable.

#### Acceptance Criteria

1. THE Game SHALL define Ghosty's Hitbox as an axis-aligned rectangle inset from the sprite bounds by Hitbox_Inset pixels on every side, so that the collision region is visually smaller than the sprite.
2. THE Game SHALL define Hitbox_Inset as a named constant.
3. WHEN Ghosty's Hitbox overlaps the bounding box of any Pipe rectangle (top or bottom segment), THE Game SHALL trigger a Wall_Collision.
4. WHEN Ghosty's Hitbox reaches or crosses the bottom boundary of the Canvas, THE Game SHALL trigger a Ground_Collision.
5. WHEN Ghosty's Hitbox reaches or crosses the top boundary of the Canvas, THE Game SHALL trigger a Ceiling_Collision.
6. WHEN a Wall_Collision, Ground_Collision, or Ceiling_Collision is detected and the Invincibility_Frame window is not active, THE Game SHALL trigger a Collision.
7. THE Game SHALL define Invincibility_Duration as a named constant representing the length in milliseconds of the Invincibility_Frame window at the start of each game session.
8. WHEN the Game_State transitions to PLAYING at the start of a new session, THE Game SHALL activate the Invincibility_Frame for Invincibility_Duration milliseconds, during which no Collision SHALL be triggered.
9. WHEN a Collision is triggered, THE Game SHALL play the Collision_Animation before setting the Game_State to GAME_OVER, so the player sees visual feedback before the Game_Over_Screen appears.
10. THE Collision_Animation SHALL consist of a brief full-Canvas white flash followed by a short screen-shake effect, completing within 500 milliseconds.
11. WHEN the Collision_Animation completes, THE Game SHALL set the Game_State to GAME_OVER and stop the Game_Loop.
12. WHEN a Collision is triggered, THE Game SHALL play the `assets/game_over.wav` sound effect at the start of the Collision_Animation.
13. WHEN a Collision is triggered, THE Game SHALL compare the current Score to the stored High_Score and update the High_Score if the current Score exceeds it.

### Requirement 5: Scoring

**User Story:** As a player, I want to see my score increase as I pass pipes, so that I have a clear sense of progress.

#### Acceptance Criteria

1. WHEN Ghosty passes the horizontal midpoint of a Pipe pair without a Collision, THE Game SHALL increment the Score by 1.
2. WHILE the Game_State is PLAYING, THE Score_Bar SHALL display the current Score.
3. THE Score_Bar SHALL display the High_Score at all times regardless of the current Game_State.
4. WHEN a new game session begins, THE Game SHALL reset the Score to 0 while retaining the High_Score.

### Requirement 6: Pause and Resume

**User Story:** As a player, I want to pause and resume the game mid-session, so that I can take a break without losing my current run.

#### Acceptance Criteria

1. WHEN the player presses Escape or P while the Game_State is PLAYING, THE Game SHALL set the Game_State to PAUSED and halt the Game_Loop.
2. WHILE the Game_State is PAUSED, THE Game SHALL render the Pause_Overlay over the Canvas displaying the text "PAUSED" and a prompt to press Escape or P to resume.
3. WHILE the Game_State is PAUSED, THE Game SHALL continue animating background clouds so the scene does not appear completely frozen.
4. WHILE the Game_State is PAUSED, THE Game SHALL halt all Pipe movement and Ghosty physics so that no game state changes occur.
5. WHEN the player presses Escape or P while the Game_State is PAUSED, THE Game SHALL set the Game_State to PLAYING and resume the Game_Loop from the exact state it was in when paused.
6. WHILE the Game_State is PAUSED, THE Game SHALL not register Flap inputs so that resuming does not inadvertently trigger a Flap.

### Requirement 7: Game Over Screen

**User Story:** As a player, I want the game over screen to clearly show my final score, my high score, whether I set a new record, and how to restart, so that I have full context on my performance.

#### Acceptance Criteria

1. WHILE the Game_State is GAME_OVER, THE Game_Over_Screen SHALL display the final Score labelled "Score".
2. WHILE the Game_State is GAME_OVER, THE Game_Over_Screen SHALL display the High_Score labelled "Best".
3. WHEN the current Score equals the High_Score and the High_Score is greater than 0, THE Game_Over_Screen SHALL display a "New Best!" indicator to inform the player a new high score was achieved.
4. WHILE the Game_State is GAME_OVER, THE Game_Over_Screen SHALL display a prompt to press Space or tap to restart.
5. WHEN the player presses Space or clicks/taps the Canvas while the Game_State is GAME_OVER, THE Game SHALL reset all game state and set the Game_State to PLAYING.
6. WHEN the game restarts, THE Game SHALL reset Ghosty's position to the horizontal and vertical center of the Canvas.
7. WHEN the game restarts, THE Game SHALL clear all existing Pipe pairs and begin generating new ones.

### Requirement 8: Persistent Score Storage

**User Story:** As a player, I want my high score to persist across sessions, so that my best performance is always remembered even after closing the browser.

#### Acceptance Criteria

1. WHEN a Collision is triggered and the current Score exceeds the stored High_Score, THE Game SHALL write the new High_Score to localStorage under a defined key before the Game_State transitions to GAME_OVER.
2. WHEN the browser loads the Game, THE Game SHALL read the High_Score from localStorage and use it as the initial High_Score value for the session.
3. IF the localStorage entry for High_Score is missing, THEN THE Game SHALL initialise the High_Score to 0 without displaying an error.
4. IF the localStorage entry for High_Score contains a value that is not a non-negative integer, THEN THE Game SHALL discard the corrupt value, initialise the High_Score to 0, and overwrite the corrupt entry with 0.
5. THE Game SHALL define the localStorage key for High_Score as a named constant so that all read and write operations reference the same key.

### Requirement 9: Visual Style

**User Story:** As a player, I want a retro sketchy visual style with rich visual feedback, so that the game has a distinctive and charming aesthetic and every action feels immediately responsive.

#### Acceptance Criteria

1. THE Game SHALL render a light blue background with a sketchy/hand-drawn texture or pattern on the Canvas.
2. THE Game SHALL render Ghosty using the sprite at `assets/ghosty.png`.
3. THE Game SHALL render Pipes as solid green rectangles with a darker green cap on the open end.
4. THE Game SHALL render the Score_Bar as a distinct strip at the bottom of the Canvas with Score and High_Score labels.
5. WHERE the browser supports it, THE Game SHALL rotate Ghosty's sprite to reflect the current vertical velocity direction, tilting down when falling and level when flapping.
6. THE Collision_Animation SHALL consist of a brief full-Canvas white flash followed by a screen-shake effect that displaces the Canvas render offset by a defined pixel amount in alternating directions, completing within 500 milliseconds total.
7. WHILE the Game_State is PLAYING, THE Game SHALL emit Particles from Ghosty's current position each frame to form a Particle_Trail, where each Particle fades from a defined initial opacity to fully transparent over a defined duration of no more than 600 milliseconds.
8. WHILE the Game_State is PLAYING, THE Game SHALL render each active Particle as a small translucent circle or ghost-shaped element at the position it was emitted, offset by its elapsed fade progress.
9. WHEN the Score increments, THE Game SHALL create a Score_Popup displaying "+1" at a defined position near the top of the Canvas, which translates upward by a defined pixel distance and fades from fully opaque to fully transparent over a defined duration of no more than 800 milliseconds before being removed.

### Requirement 10: Audio

**User Story:** As a player, I want sound effects for flapping, scoring, and game over, plus looping background music during play, so that the game feels responsive and alive.

#### Acceptance Criteria

1. THE Game SHALL load `assets/jump.wav` and `assets/game_over.wav` at startup.
2. IF an audio file fails to load, THEN THE Game SHALL continue operating without sound and SHALL NOT display an error to the player.
3. WHEN the Flap action is triggered, THE Game SHALL restart the `jump.wav` playback from the beginning so rapid flaps each produce a sound.
4. WHEN the Score increments, THE Game SHALL play a distinct short sound effect to provide immediate auditory feedback that a point was scored.
5. THE Game SHALL define the background music asset path as a named constant representing the file path from which Background_Music is loaded.
6. WHEN the Game initialises, THE Game SHALL attempt to load the Background_Music from the configured asset path.
7. IF the Background_Music file is absent or fails to load, THEN THE Game SHALL continue operating without background music and SHALL NOT display an error to the player.
8. WHEN the Game_State transitions to PLAYING, THE Game SHALL begin playing the Background_Music as a looping track if it was successfully loaded.
9. WHEN the Game_State transitions to PAUSED, THE Game SHALL pause Background_Music playback at its current position.
10. WHEN the Game_State transitions from PAUSED to PLAYING, THE Game SHALL resume Background_Music playback from the position at which it was paused.
11. WHEN the Game_State transitions to GAME_OVER, THE Game SHALL stop Background_Music playback and reset its position to the beginning.

### Requirement 11: Parallax Cloud Background

**User Story:** As a player, I want to see clouds drifting at different speeds in the background, so that the game feels like it has depth and visual richness.

#### Acceptance Criteria

1. THE Game SHALL render at least two distinct Cloud_Layers on the Canvas behind Pipes and Ghosty.
2. WHILE the Game is active (any Game_State), THE Game_Loop SHALL scroll each Cloud_Layer leftward at a different horizontal speed, with layers further in the background moving slower than layers closer to the foreground.
3. THE Game SHALL render each Cloud as a semi-transparent white shape with an opacity value strictly less than 1.0, so that the background colour remains visible through the Cloud.
4. WHEN a Cloud exits the left edge of the Canvas, THE Game SHALL reposition that Cloud to the right edge of the Canvas to maintain a continuous stream.
5. THE Game SHALL distribute Clouds across each layer at randomised horizontal intervals so that no two Clouds in the same layer start at the same position.
6. WHILE the Game_State is PAUSED, THE Game_Loop SHALL continue scrolling Cloud_Layers so that the background remains animated.

### Requirement 12: Responsive Layout

**User Story:** As a player, I want the game to fit my screen, so that I can play on both desktop and mobile browsers.

#### Acceptance Criteria

1. THE Game SHALL size the Canvas to fill the full width and height of the browser viewport on load.
2. WHEN the browser viewport is resized, THE Game SHALL resize the Canvas and scale all game elements proportionally.
3. THE Game SHALL accept both keyboard input (Space key) and pointer input (mouse click or touch tap) for all player actions.
