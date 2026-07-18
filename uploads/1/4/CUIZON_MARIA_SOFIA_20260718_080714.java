import java.util.Scanner;

public class StudentGradeSystem {
 

static String getRemark(int grade){

if(grade >= 90) return "Excellent";
if(grade >= 80) return "Verry Good";
if(grade == 76) return "Good";
if(grade >= 75) return "Passed";
if(grade >= 0) return "Failed";
return "Invalid Grade";
}
public static void main(String[] args) {
Scanner sc = new Scanner(System.in);

for(int i = 1; i <=5; i++) {
 System.out.print("Student" + i);
 
 System.out.print("Enter your Name:");
 String name = sc.nextLine();
 
 System.out.print("Enter your grade:");
 int grade = sc.nextInt();
 sc.nextLine(); 
 
 System.out.println("\nName:" + name);
 
 System.out.println("Grade: " + grade);
 
 System.out.println("Remark:" + getRemark(grade));
 
    System.out.println();
   }

     sc.close();
  }

}