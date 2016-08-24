import os
import json
import ConfigParser
from supervisor.supervisorctl import ControllerPluginBase


class TwiddlerControllerPlugin(ControllerPluginBase):
    def __init__(self, controller, **config):
        self.ctl = controller
        self.twiddler = controller.get_server_proxy().twiddler
        self.supervisor = controller.get_server_proxy().supervisor
        self.config_dir = config["config_dir"]

    #
    #   add_program

    def do_add_program(self, args):
        if 1 > len(args.split()) > 2:
            self.help_add_program()

        if len(args.split()) == 1:  # read options from file
            program_group = args

            if program_group not in self.twiddler.getGroupNames():
                self.ctl.output("{} was not found.".format(program_group))
                self.help_add_program()
                return

            programs = self.supervisor.getAllProcessInfo()
            program_names = [x["name"] for x in programs if x["group"] == program_group]

            worker_num = str(0)
            for i in xrange(0, len(program_names)):
                worker_num = str(i)
                if worker_num not in program_names:
                    break
                worker_num = str(i + 1)

            config = ConfigParser.ConfigParser()
            config.read(os.path.join(self.config_dir, program_group + ".conf"))

            program_options = dict(config._sections["program:" + program_group])
            program_options.pop('numprocs', None)
            program_options.pop('process_name', None)

            self.twiddler.addProgramToGroup(program_group, worker_num, program_options)
            self.ctl.output("{}:{} was added.".format(program_group, worker_num))
        else:
            program_group, program_options = args.split()
            try:
                program_options = json.loads(program_options)
            except ValueError, e:
                print e, program_options
                return

            if program_group not in self.twiddler.getGroupNames():
                self.twiddler.addGroup(program_group)

            self.twiddler.addProgramToGroup(program_group, program_options.get("name", program_group), program_options)
            self.ctl.output("{}:{}: added.".format(program_group, program_options.get("name")))

    def help_add_program(self):
        self.ctl.output("add_program <group_name> [options]\n"
                        "Add program from the following groups:\n{}".format("\n".join(self.twiddler.getGroupNames())))

    #
    #   del_program

    def do_del_program(self, args):
        if not args:
            self.help_del_program()
            return

        program_name = None
        if ":" in args:
            program_group, program_name = args.split(":")
        else:
            program_group = args

        # check if group exists
        if program_group not in [x["group"] for x in self.supervisor.getAllProcessInfo()]:
            self.ctl.output("{} was not found.".format(program_group))
            self.help_del_program()
            return

        programs = self.supervisor.getAllProcessInfo()
        program_names = [x["name"] for x in programs if x["group"] == program_group]
        if not program_name:  # delete last one
            program_name = sorted(program_names)[-1]
            self._del_program(program_group, program_name)
        elif program_name == "*":  # delete all
            for program_name in program_names:
                self._del_program(program_group, program_name)
        else:  # delete selected program
            if program_name not in program_names:
                self.ctl.output("{} was not found.".format(program_name))
                self.help_del_program()
                return

            self._del_program(program_group, program_name)

    def help_del_program(self):
        self.ctl.output("del_program <group_name[:process_num]>\n"
                        "Delete program from the following:\n{}".format(
            "\n".join([x["group"] + ":" + x["name"] for x in self.supervisor.getAllProcessInfo()])))

    def _del_program(self, group, name):
        full_name = group + ":" + name
        worker_info = self.supervisor.getProcessInfo(full_name)
        if worker_info["statename"] == "RUNNING":
            self.supervisor.stopProcess(full_name)

        self.twiddler.removeProcessFromGroup(group, name)
        self.ctl.output("{}:{} was removed.".format(group, name))


def make_twiddler_controllerplugin(controller, **config):
    return TwiddlerControllerPlugin(controller, **config)
