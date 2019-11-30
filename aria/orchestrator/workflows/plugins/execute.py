from aria import workflow
from aria.orchestrator.workflows.api import task
from aria.orchestrator.workflows.exceptions import TaskException

@workflow
def simple_execute(ctx, graph, interface_name, operation_name):
    for node in ctx.model.node.iter():
        try:
            graph.add_tasks(task.OperationTask(node, interface_name, operation_name))
        except TaskException:
            pass
