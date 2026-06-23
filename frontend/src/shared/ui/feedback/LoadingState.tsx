export default function LoadingState({ message = "加载中..." }: { message?: string }) {
  return <div className="text-center py-8 text-muted-foreground">{message}</div>;
}
