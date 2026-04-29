# I have zero clue what I am doing
import math
import dearpygui.dearpygui as dpg
import scipy.constants as sci_const


#
# Simulator settings
#

class AppContext:
    # helper functions
    def set_pendulum(default, to_set):
        to_set["L"] = default["L"]
        to_set["state"]["theta"] = default["theta"]
        to_set["state"]["omega"] = default["omega"]

        to_set["state"]["data_t"] = []
        to_set["state"]["data_theta"] = []
        to_set["state"]["data_omega"] = []
        to_set["state"]["current_t"] = 0.0

    DIMS = [1470, 1200]
    FPS = 60
    DRAW_DIMS = [600, 450]
    SIM_GRAV_MULT = 20
    PLOT_LIMIT = 500

    # Changeable variables
    sim_is_running = False

    # Selectable variables
    selected = "pendulum"
    sim_speed = 1

    default_vals = {
        "pendulum": {
            "theta": math.pi / 4,
            "omega": 0.0,
            "L": 200,
        }
    }

    sim = {
        "pendulum": {
            "pivot": [round(DRAW_DIMS[0] / 2), round(DRAW_DIMS[1] / 3)],   # Pendulum pivot
            "L": None,                                                     # Pendulum height
            "g": sci_const.g,                                              # Gravitational accel
            "dt": 1 / FPS,                                                 # Time delta
            "damping_type": "Undamped",
            "state": {                                                     # Hold variable-states
                "theta": None,                                             # Pendulum deviation from pi/4
                "omega": None,                                             # Angular velocity,
                "data_t": [],
                "data_theta": [],
                "persistent_data_omega": [],
                "persistent_data_theta": [],
                "data_omega": [],
                "current_t": 0.0
            }
        }
    }

    set_pendulum(default_vals["pendulum"], sim["pendulum"])

#
# Rendering calculations
#

def clamp_plot_limits(axis_tag, min_bound, max_bound):
    current_limits = dpg.get_axis_limits(axis_tag)
    new_limits = [current_limits[0], current_limits[1]]
    modified = False

    # Pokud je levá mez moc vlevo
    if current_limits[0] < min_bound:
        new_limits[0] = min_bound
        modified = True
    
    # Pokud je pravá mez moc vpravo
    if current_limits[1] > max_bound:
        new_limits[1] = max_bound
        modified = True

    # Pokud jsme něco změnili, pošleme to zpět do grafu
    if modified:
        dpg.set_axis_limits(axis_tag, new_limits[0], new_limits[1])


def update_render(c: AppContext):
    match c.selected:
        case "pendulum":
            #
            # Pendulum calculation
            #

            config = c.sim["pendulum"]
            state = config["state"]
            target_dt = config["dt"] * c.sim_speed
            steps = int(c.sim_speed * 5)
            sub_dt = target_dt / steps

            # Výpočet vlastní frekvence (omega_0) pro určení kritického útlumu
            w0 = math.sqrt((c.SIM_GRAV_MULT * config["g"]) / config["L"])

            # Nastavení koeficientu útlumu gamma podle vybraného typu
            damping_type = config["damping_type"]
            if damping_type == "Undamped":
                gamma = 0.0
            elif damping_type == "Underdamped":
                gamma = 0.3 * w0  # Menší než 2*w0
            elif damping_type == "Critically damped":
                gamma = 2.0 * w0  # Přesně 2*w0
            elif damping_type == "Overdamped":
                gamma = 6.0 * w0  # Větší než 2*w0

            for _ in range(steps):
                # Zrychlení = gravitační složka - tlumící složka
                alpha = -(w0**2) * math.sin(state["theta"]) - (gamma * state["omega"])
                state["omega"] += alpha * sub_dt
                state["theta"] += state["omega"] * sub_dt

            #
            # Pendulum animation rendering
            #

            x = config["pivot"][0] + config["L"] * math.sin(state["theta"])
            y = config["pivot"][1] + config["L"] * math.cos(state["theta"])

            dpg.configure_item("rod", p2=[x, y])
            dpg.configure_item("bob", center=[x, y])

            #
            # Pendulum graph rendering
            #

            state["current_t"] += target_dt
            state["data_t"].append(state["current_t"])
            state["data_theta"].append(state["theta"])
            state["persistent_data_theta"].append(state["theta"])

            if len(state["data_t"]) > c.PLOT_LIMIT:
                state["data_t"].pop(0)
                state["data_theta"].pop(0)
                state["data_omega"].pop(0)

                if damping_type == "Undamped":
                    state["persistent_data_omega"].pop(0)
                    state["persistent_data_theta"].pop(0)

            dpg.set_value("series_tag", [state["data_t"], state["data_theta"]])
            dpg.fit_axis_data("x_axis")

            #
            # Phase plane rendering
            #

            state["data_omega"].append(state["omega"])
            state["persistent_data_omega"].append(state["omega"])
            dpg.set_value("phase_series", [state["persistent_data_theta"], state["persistent_data_omega"]])
            dpg.set_value("current_state_series", (state["theta"], state["omega"]))

            clamp_plot_limits("x_axis_phase", -10.0, 10.0) 
            clamp_plot_limits("y_axis_omega", -10.0, 10.0)


def app_setup():
    # Spawning App context settings
    context = AppContext

    # Setting DearPyGUI
    dpg.create_context()
    dpg.create_viewport(title="Harmonic Oscillator", width=context.DIMS[0], height=context.DIMS[1])

    return context


def elements_setup(c: AppContext):
    #
    # Simulation settings
    #

    def handle_slider_speed(sender, app_data):
        step = 0.5
        snapped_val = round(app_data / step) * step
        dpg.set_value(sender, snapped_val)
        c.sim_speed = snapped_val

    def handle_slider_length(sender, app_data):
        c.default_vals["pendulum"]["L"] = app_data
        reset_sim()

    def handle_slider_theta(sender, app_data):
        # Převod ze stupňů na radiány pro fyziku
        c.default_vals["pendulum"]["theta"] = math.radians(app_data)
        reset_sim()

    def handle_listbox(sender, app_data):
        c.sim["pendulum"]["damping_type"] = app_data
        reset_sim()

    def start_sim():
        c.sim_is_running = True

    def stop_sim():
        c.sim_is_running = False

    def reset_sim():
        # Reset normally persisting variables
        c.sim["pendulum"]["state"]["persistent_data_omega"] = []
        c.sim["pendulum"]["state"]["persistent_data_theta"] = []

        c.set_pendulum(c.default_vals["pendulum"], c.sim["pendulum"])

        if dpg.does_item_exist("x_axis_phase"):
            dpg.set_axis_limits("x_axis_phase", -3.5, 3.5)
        if dpg.does_item_exist("y_axis_omega"):
            dpg.set_axis_limits("y_axis_omega", -3.5, 3.5)

        update_render(c)

    with dpg.window(label="Simulator settings", pos=[0, 0]):
        dpg.add_text("Oscillator is set to: Pendulum")

        with dpg.group(horizontal=True):
            dpg.add_button(label="Start sim", callback=start_sim)
            dpg.add_button(label="Stop sim", callback=stop_sim)
            dpg.add_button(label="Reset", callback=reset_sim)

        dpg.add_text("Simulation speed:")
        dpg.add_slider_float(
            default_value=1.0,
            min_value=0.5,
            max_value=5.0,
            callback=handle_slider_speed
        )

        dpg.add_text("Pendulum length:")
        dpg.add_slider_float(
            default_value=200.0,
            min_value=50.0,
            max_value=280.0,
            callback=handle_slider_length
        )

        dpg.add_text("Initial angle:")
        dpg.add_slider_float(
            default_value=45.0,
            min_value=-170.0,
            max_value=170.0,
            callback=handle_slider_theta
        )

        dpg.add_text("Pendulum oscillation:")
        dpg.add_listbox(
            items=["Undamped", "Underdamped", "Overdamped", "Critically damped"],
            default_value="Undamped",
            callback=handle_listbox,
            num_items=4,
            tag="oscillator_select"
        )

    #
    # Oscillator render
    #

    pendulum_state = c.sim["pendulum"]
    with dpg.window(label="Oscillator state", pos=[230, 0]):
        with dpg.drawlist(width=c.DRAW_DIMS[0], height=c.DRAW_DIMS[1]):
            dpg.draw_line(pendulum_state["pivot"], [400, 300], color=(200, 200, 200, 255), thickness=2, tag="rod")
            dpg.draw_circle(
                center=[400, 300],
                radius=15,
                fill=(50, 150, 255, 255),
                color=(255, 255, 255, 255),
                tag="bob")

            dpg.draw_circle(center=pendulum_state["pivot"], radius=4, fill=(255, 255, 255, 255))

    #
    # Oscillator deviation render
    #

    with dpg.window(label="Oscillator deviation graph", pos=[850, 0]):
        with dpg.plot(label="Theta/Time graph", width=c.DRAW_DIMS[0], height=c.DRAW_DIMS[1]):
            dpg.add_plot_legend()

            dpg.add_plot_axis(dpg.mvXAxis, label="Time [s]", tag="x_axis")

            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Theta [rad]")
            dpg.set_axis_limits(y_axis, -1.5, 1.5)
            dpg.add_line_series(
                c.sim["pendulum"]["state"]["data_t"],
                c.sim["pendulum"]["state"]["data_theta"],
                label="Deviation",
                parent=y_axis,
                tag="series_tag"
            )

    #
    # Phase plane rendering
    #

    with dpg.window(label="Phase portrait (Theta/Omega)", pos=[230, 500]):
        with dpg.plot(width=c.DRAW_DIMS[0], height=c.DRAW_DIMS[1]):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Position (theta)", tag="x_axis_phase")

            with dpg.plot_axis(dpg.mvYAxis, label="Velocity (omega)", tag="y_axis_omega"):
                dpg.add_line_series([], [], label="Phase Trajectory", tag="phase_series")

            dpg.add_drag_point(
                label="Current State",
                tag="current_state_series",
                default_value=(0.0, 0.0),
                color=[255, 165, 0, 255],
                thickness=8.0,
            )


def app_mainloop(c: AppContext):
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Simulator state updates
    while dpg.is_dearpygui_running():
        if c.sim_is_running:
            update_render(c)
        dpg.render_dearpygui_frame()

    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    # Main app code

    # Environment setup
    app_context = app_setup()

    # Elements setup
    elements_setup(app_context)

    # Mainloop
    app_mainloop(app_context)
